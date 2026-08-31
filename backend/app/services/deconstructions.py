"""Prepare and render Deconstruction drafts from stored Evidence only."""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from uuid import uuid4

from PIL import Image

from app.agents import deconstruction as writer
from app.agents import prompts
from app.config import settings
from app.domain import deconstruction as rules
from app.domain.entities import (
    Analysis,
    Deconstruction,
    DeconstructionEvidence,
    DeconstructionSourceType,
    DeconstructionStatus,
    DeconstructionWriting,
    Experiment,
    ExperimentStatus,
    ShootRecord,
    Shot,
    ShotKind,
    now,
)
from app.imaging import canvas, visual_evidence
from app.imaging import deconstruction as renderer
from app.infra import repository as repo
from app.infra.storage import ORIGINAL, deconstruction_blob_path, visual_evidence_blob_path
from app.services.context import Context

logger = logging.getLogger(__name__)


class DeconstructionConflict(ValueError):
    pass


class DeconstructionUnavailable(RuntimeError):
    pass


async def prepare(
    ctx: Context,
    user_id: str,
    source_type: DeconstructionSourceType,
    source_id: str,
    source_revision: int = 0,
    cover_shot_id: str = "",
) -> Deconstruction:
    source, shots = await _source(ctx, user_id, source_type, source_id, source_revision)
    return await _prepare_loaded(
        ctx,
        user_id,
        source_type,
        source_id,
        source_revision,
        cover_shot_id,
        source,
        shots,
    )


async def prepare_shoot_record(ctx: Context, record: ShootRecord) -> Deconstruction:
    """Create the replay-safe needs-cover artifact before the Shoot Record settles."""
    shots = await _shots(ctx, record.user_id, record.shot_ids)
    return await _prepare_loaded(
        ctx,
        record.user_id,
        DeconstructionSourceType.SHOOT,
        record.shoot_id,
        record.revision,
        "",
        record,
        shots,
    )


async def prepare_experiment_record(ctx: Context, experiment: Experiment) -> Deconstruction:
    """Create one replay-safe needs-cover artifact from a terminal Experiment."""
    if experiment.status is ExperimentStatus.OPEN:
        raise DeconstructionConflict("A terminal Experiment Record is required")
    if not experiment.result_shot_ids:
        raise DeconstructionConflict("An Experiment result Shot is required")
    shots = await _shots(
        ctx,
        experiment.user_id,
        [experiment.reference_shot_id, *experiment.result_shot_ids],
    )
    return await _prepare_loaded(
        ctx,
        experiment.user_id,
        DeconstructionSourceType.EXPERIMENT,
        experiment.id,
        1,
        "",
        experiment,
        shots,
    )


async def _prepare_loaded(
    ctx: Context,
    user_id: str,
    source_type: DeconstructionSourceType,
    source_id: str,
    source_revision: int,
    cover_shot_id: str,
    source: Shot | ShootRecord | Experiment,
    shots: list[Shot],
) -> Deconstruction:
    candidates = (
        [source_id]
        if source_type is DeconstructionSourceType.SHOT
        else [
            shot_id
            for shot_id in rules.cover_candidates(shots)
            if (shot := next((item for item in shots if item.id == shot_id), None)) is not None
            and ORIGINAL in shot.blobs
        ]
    )
    if source_type is DeconstructionSourceType.SHOT and cover_shot_id not in ("", source_id):
        raise DeconstructionConflict("A Shot story must use that same Shot as its opening.")
    draft_id = _draft_id(source_type, source_id, source_revision)
    existing = await repo.find_deconstruction(ctx.store, draft_id)
    draft = Deconstruction(
        id=draft_id,
        user_id=user_id,
        source_type=source_type,
        source_id=source_id,
        source_revision=source_revision,
        candidate_cover_shot_ids=candidates,
        rendering_version=renderer.RENDER_VERSION,
    )
    created = await ctx.store.create(repo.DECONSTRUCTIONS, draft_id, draft.model_dump(mode="json"))
    existing = await repo.find_deconstruction(ctx.store, draft_id)
    if existing is None or existing.user_id != user_id:
        raise repo.UnknownEntity("Deconstruction not found")
    if created:
        await _event(ctx, existing, "needs_cover")
    if not cover_shot_id:
        # Settlement and repeat reads must not erase a writer or a completed draft.
        await ctx.store.patch_if(
            repo.DECONSTRUCTIONS,
            draft_id,
            {"candidate_cover_shot_ids": candidates},
            {"user_id": user_id},
        )
        return existing.model_copy(update={"candidate_cover_shot_ids": candidates})
    if cover_shot_id not in candidates:
        label = "Shoot" if source_type is DeconstructionSourceType.SHOOT else "Experiment"
        raise DeconstructionConflict(f"Choose a cover from the Shots you marked in this {label}")

    cover = next(shot for shot in shots if shot.id == cover_shot_id)
    analysis = await repo.find_analysis(ctx.store, cover_shot_id)
    if analysis is None:
        raise DeconstructionConflict(
            "This Shot needs its visual reading before a story can be made."
        )
    try:
        original_bytes = await ctx.blobs.read(cover.blobs[ORIGINAL])
        original = await asyncio.to_thread(canvas.load_bytes, original_bytes)
    except Exception as exc:
        raise DeconstructionUnavailable(
            "The original Shot could not be opened. Please try again."
        ) from exc
    try:
        evidence, artifact_images = await load_story_evidence(
            ctx, cover, analysis, original_bytes, original
        )
    except rules.UnsupportedStory as exc:
        raise DeconstructionConflict(str(exc)) from exc
    input_digest = writing_input_digest(
        source_type, source_id, source_revision, cover, analysis, original_bytes, evidence
    )
    if await _ready(ctx, existing, input_digest):
        return existing

    lease = uuid4().hex
    claimed_at = now()
    lease_until = claimed_at + timedelta(seconds=settings.deconstruction_lease_seconds)

    def claim(document: dict) -> dict | None:
        expires = document.get("_writing_until")
        if expires and datetime.fromisoformat(expires) > claimed_at:
            return None
        return {
            **document,
            "_writing_token": lease,
            "_writing_until": lease_until.isoformat(),
        }

    document, claimed = await ctx.store.mutate(repo.DECONSTRUCTIONS, draft_id, claim)
    if not claimed or document is None:
        raise DeconstructionConflict("This story is already being prepared. Give it a moment.")
    existing = Deconstruction.model_validate(document)
    try:
        if await _ready(ctx, existing, input_digest):
            return existing
        writing = existing.writing
        if writing is None or writing.input_digest != input_digest:
            await _event(ctx, existing, "writing")
            model_image = canvas.to_jpeg_bytes(
                canvas.fit_for_model(original, settings.analyst_max_edge), quality=90
            )
            started = time.monotonic()
            detail_sheet = await asyncio.to_thread(
                renderer.detail_contact_sheet, original, evidence, cover.grid
            )
            artifact_sheet = await asyncio.to_thread(
                renderer.artifact_contact_sheet, evidence, artifact_images
            )
            story = await writer.write(
                user_id,
                evidence,
                model_image,
                canvas.to_jpeg_bytes(detail_sheet, quality=90) if detail_sheet else None,
                canvas.to_jpeg_bytes(artifact_sheet, quality=90) if artifact_sheet else None,
            )
            try:
                rules.story_pages(
                    story,
                    evidence,
                    cover_shot_id,
                    max_beats=settings.deconstruction_max_story_pages,
                )
            except rules.UnsupportedStory:
                logger.warning(
                    "Deconstruction visual selections rejected: %s",
                    json.dumps(
                        {
                            "shot_id": cover_shot_id,
                            "available_details": [item.id for item in evidence if item.cells],
                            "available_artifacts": list(artifact_images),
                            "selections": [
                                {
                                    "evidence_ids": beat.evidence_ids,
                                    "detail": beat.detail_evidence_id,
                                    "artifact": beat.artifact_evidence_id,
                                }
                                for beat in ([story.opening] if story.opening else []) + story.beats
                            ],
                        }
                    ),
                )
                raise
            writing = DeconstructionWriting(
                input_digest=input_digest,
                cover_shot_id=cover_shot_id,
                model=settings.model_flash,
                prompt_version=prompts.version("deconstruction"),
                story=story,
                evidence=evidence,
                elapsed_seconds=round(time.monotonic() - started, 3),
            )
            # Commit the validated writing BEFORE the first JPEG is rendered.
            if not await ctx.store.patch_if(
                repo.DECONSTRUCTIONS,
                draft_id,
                {"writing": writing.model_dump(mode="json"), "error": ""},
                {"_writing_token": lease},
            ):
                raise DeconstructionConflict("A newer story request replaced this one.")
            existing = existing.model_copy(update={"writing": writing})
            await _event(ctx, existing, "written")

        pages = rules.story_pages(
            writing.story,
            evidence,
            cover_shot_id,
            max_beats=settings.deconstruction_max_story_pages,
        )
        digest = _render_digest(writing)
        # Content-addressed files: a failed rebuild never deletes an older draft.
        for index, page in enumerate(pages, 1):
            rendered = await asyncio.to_thread(
                renderer.render,
                page,
                [original],
                index,
                len(pages),
                cover.grid,
                artifact_image=artifact_images.get(page.artifact_evidence_id),
            )
            payload = await asyncio.to_thread(
                canvas.to_jpeg_bytes, rendered, quality=95 if page.kind.value == "clean" else 92
            )
            path = deconstruction_blob_path(user_id, draft_id, index, digest)
            await ctx.blobs.write(path, payload, "image/jpeg")
            page.blob_path = path
        drafted = existing.model_copy(
            update={
                "status": DeconstructionStatus.DRAFTED,
                "candidate_cover_shot_ids": candidates,
                "cover_shot_id": cover_shot_id,
                "pages": pages,
                "suggested_caption": writing.story.caption,
                "input_digest": digest,
                "rendering_version": renderer.RENDER_VERSION,
                "writing": writing,
                "error": "",
                "updated_at": now(),
            }
        )
        if not await ctx.store.patch_if(
            repo.DECONSTRUCTIONS,
            draft_id,
            drafted.model_dump(mode="json"),
            {"_writing_token": lease},
        ):
            raise DeconstructionConflict("A newer story request replaced this one.")
        await _event(ctx, drafted, "drafted")
        return drafted
    except DeconstructionConflict:
        raise
    except Exception as exc:
        logger.exception("Deconstruction %s failed", draft_id)
        if isinstance(exc, rules.UnsupportedStory):
            message = str(exc)
        elif isinstance(exc, TimeoutError):
            message = "The story writer took too long. Try again; your Shot has not changed."
        else:
            message = (
                "The story could not be prepared. Please try again; your Shot has not changed."
            )
        failed = existing.model_copy(
            update={
                "status": (
                    DeconstructionStatus.DRAFTED
                    if existing.status is DeconstructionStatus.DRAFTED
                    else DeconstructionStatus.FAILED
                ),
                "error": message,
                "updated_at": now(),
            }
        )
        if await ctx.store.patch_if(
            repo.DECONSTRUCTIONS,
            draft_id,
            {
                "status": failed.status.value,
                "error": message,
                "updated_at": failed.updated_at.isoformat(),
            },
            {"_writing_token": lease},
        ):
            await _event(ctx, failed, "failed")
        raise DeconstructionUnavailable(message) from exc
    finally:
        await ctx.store.patch_if(
            repo.DECONSTRUCTIONS,
            draft_id,
            {"_writing_token": "", "_writing_until": ""},
            {"_writing_token": lease},
        )


async def load_story_evidence(
    ctx: Context,
    cover: Shot,
    analysis: Analysis,
    original_bytes: bytes,
    original: Image.Image,
) -> tuple[list[DeconstructionEvidence], dict[str, Image.Image]]:
    """Offer only source-matched artifacts whose exact files are readable now.

    Work on copied Evidence. Missing visual support must not rewrite the Analysis
    or cause Scribe to generate a replacement diagram.
    """
    evidence = rules.evidence_for(
        cover,
        analysis,
        max_items=settings.deconstruction_max_evidence,
        min_agreement=settings.panel_min_agreement,
        min_confidence=settings.panel_min_confidence,
        max_details=settings.deconstruction_max_details,
        source_digest=hashlib.sha256(original_bytes).hexdigest()[:24],
        artifact_renderer_version=visual_evidence.RENDERER_VERSION,
    )
    images: dict[str, Image.Image] = {}
    for item in evidence:
        artifact = item.visual_artifact
        if artifact is None:
            continue
        expected_path = visual_evidence_blob_path(
            cover.user_id, cover.id, item.id.removeprefix("technique_")
        )
        if (
            artifact.blob_path != expected_path
            or len(images) >= settings.deconstruction_max_artifacts
        ):
            item.visual_artifact = None
            continue
        try:
            payload = await ctx.blobs.read(expected_path)
            image = await asyncio.to_thread(canvas.load_bytes, payload)
            # Current renderers resize the whole frame. Reject mismatched framing.
            if abs(image.width * original.height - image.height * original.width) > max(
                original.size
            ):
                raise ValueError("Artifact framing differs from the selected Shot")
        except Exception as exc:
            logger.warning(
                "Deconstruction omitted %s/%s visual artifact: %s",
                cover.id,
                item.id,
                type(exc).__name__,
            )
            item.visual_artifact = None
            continue
        item.artifact_sha256 = hashlib.sha256(payload).hexdigest()
        images[item.id] = image
    return evidence, images


def writing_input_digest(
    source_type: DeconstructionSourceType,
    source_id: str,
    source_revision: int,
    cover: Shot,
    analysis: Analysis,
    original: bytes,
    evidence: list[DeconstructionEvidence],
) -> str:
    """Fingerprint every writer input; unrelated Shoot counts cannot change its story."""
    return _digest(
        {
            "source_type": source_type.value,
            "source_id": source_id,
            "revision": source_revision,
            "cover": cover.id,
            "grid": cover.grid,
            "analysis": analysis,
            "available_evidence": [item.model_dump(mode="json") for item in evidence],
            "image_sha256": hashlib.sha256(original).hexdigest(),
            "plan_version": rules.PLAN_VERSION,
            "model": settings.model_flash,
            "prompt_version": prompts.version("deconstruction"),
            "max_beats": settings.deconstruction_max_story_pages,
            "max_evidence": settings.deconstruction_max_evidence,
            "max_details": settings.deconstruction_max_details,
            "max_artifacts": settings.deconstruction_max_artifacts,
            "min_agreement": settings.panel_min_agreement,
            "min_confidence": settings.panel_min_confidence,
            "image_max_edge": settings.analyst_max_edge,
        }
    )


async def _ready(ctx: Context, draft: Deconstruction, input_digest: str) -> bool:
    if (
        draft.status is not DeconstructionStatus.DRAFTED
        or draft.writing is None
        or draft.writing.input_digest != input_digest
        or draft.cover_shot_id != draft.writing.cover_shot_id
        or draft.input_digest != _render_digest(draft.writing)
        or draft.rendering_version != renderer.RENDER_VERSION
        or not draft.pages
        or any(not page.blob_path for page in draft.pages)
    ):
        return False
    return all(await asyncio.gather(*(ctx.blobs.exists(page.blob_path) for page in draft.pages)))


def _render_digest(writing: DeconstructionWriting) -> str:
    return _digest(
        {
            "writing_digest": writing.input_digest,
            "story": writing.story,
            "rendering_version": renderer.RENDER_VERSION,
        }
    )


async def _source(
    ctx: Context,
    user_id: str,
    source_type: DeconstructionSourceType,
    source_id: str,
    source_revision: int,
) -> tuple[Shot | ShootRecord | Experiment, list[Shot]]:
    if source_type is DeconstructionSourceType.SHOT:
        if source_revision != 1:
            raise DeconstructionConflict("A Shot story uses source revision 1.")
        shot = await _owned_shot(ctx, user_id, source_id)
        if shot.kind is not ShotKind.PHOTO:
            raise DeconstructionConflict("Visual stories currently support still Shots only.")
        if not shot.blobs.get(ORIGINAL):
            raise DeconstructionConflict("This Shot needs its original before a story can be made.")
        return shot, [shot]
    if source_type is DeconstructionSourceType.SHOOT:
        if source_revision < 1:
            raise DeconstructionConflict("A settled Shoot revision is required")
        source = await repo.find_shoot_record(ctx.store, source_id, source_revision)
        if source is None or source.user_id != user_id:
            raise repo.UnknownEntity(f"Shoot Record {source_id} revision {source_revision}")
        shot_ids = source.shot_ids
    else:
        if source_revision != 1:
            raise DeconstructionConflict("A terminal Experiment revision is required")
        source = await repo.find_experiment(ctx.store, source_id)
        if source is None or source.user_id != user_id:
            raise repo.UnknownEntity(f"Experiment {source_id}")
        if source.status is ExperimentStatus.OPEN:
            raise DeconstructionConflict("A terminal Experiment Record is required")
        shot_ids = [source.reference_shot_id, *source.result_shot_ids]
    return source, await _shots(ctx, user_id, shot_ids)


async def _owned_shot(ctx: Context, user_id: str, shot_id: str) -> Shot:
    shot = await repo.find_shot(ctx.store, shot_id)
    if shot is None or shot.user_id != user_id or shot.superseded_by_inspiration_id:
        raise repo.UnknownEntity("Shot not found")
    return shot


async def for_shot(ctx: Context, user_id: str, shot_id: str) -> Deconstruction | None:
    """Read only; opening a Shot never creates a draft or starts the writer."""
    await _owned_shot(ctx, user_id, shot_id)
    draft = await repo.find_deconstruction(
        ctx.store, _draft_id(DeconstructionSourceType.SHOT, shot_id, 1)
    )
    return draft if draft is not None and draft.user_id == user_id else None


async def _shots(ctx: Context, user_id: str, shot_ids: list[str]) -> list[Shot]:
    shots: list[Shot] = []
    for shot_id in dict.fromkeys(item for item in shot_ids if item):
        shot = await repo.find_shot(ctx.store, shot_id)
        if shot is not None and shot.user_id == user_id and not shot.superseded_by_inspiration_id:
            shots.append(shot)
    return shots


async def _event(ctx: Context, draft: Deconstruction, stage: str) -> None:
    await repo.record(
        ctx.store,
        draft.user_id,
        "scribe",
        f"deconstruction_{stage}",
        {
            "deconstruction_id": draft.id,
            "source_type": draft.source_type.value,
            "source_id": draft.source_id,
            "source_revision": draft.source_revision,
            "pages": len(draft.pages),
            "writing_model": draft.writing.model if draft.writing else "",
            "writing_prompt_version": draft.writing.prompt_version if draft.writing else "",
            "writing_seconds": draft.writing.elapsed_seconds if draft.writing else None,
            "visual_artifact_pages": sum(page.visual_layer == "artifact" for page in draft.pages),
        },
        experiment_id=(
            draft.source_id if draft.source_type is DeconstructionSourceType.EXPERIMENT else ""
        ),
        shot_id=draft.source_id if draft.source_type is DeconstructionSourceType.SHOT else "",
    )


def _draft_id(source_type: DeconstructionSourceType, source_id: str, revision: int) -> str:
    value = f"{source_type.value}:{source_id}:{revision}".encode()
    return f"deconstruction_{hashlib.sha256(value).hexdigest()[:24]}"


def _digest(value) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, dict):
        value = {
            key: item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for key, item in value.items()
        }
        if isinstance(value.get("pages"), list):
            value["pages"] = [
                item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                for item in value["pages"]
            ]
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
