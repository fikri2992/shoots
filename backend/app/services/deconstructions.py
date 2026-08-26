"""Prepare and render Deconstruction drafts from stored Evidence only."""

import hashlib
import json

from app.domain import deconstruction as rules
from app.domain.entities import (
    Deconstruction,
    DeconstructionSourceType,
    DeconstructionStatus,
    Experiment,
    ShootRecord,
    Shot,
    now,
)
from app.imaging import canvas
from app.imaging import deconstruction as renderer
from app.infra import repository as repo
from app.infra.storage import (
    ANNOTATED,
    ORIGINAL,
    deconstruction_blob_path,
    deconstruction_blob_prefix,
)
from app.services.context import Context


class DeconstructionConflict(ValueError):
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


async def _prepare_loaded(
    ctx: Context,
    user_id: str,
    source_type: DeconstructionSourceType,
    source_id: str,
    source_revision: int,
    cover_shot_id: str,
    source: ShootRecord | Experiment,
    shots: list[Shot],
) -> Deconstruction:
    candidates = [
        shot_id
        for shot_id in rules.cover_candidates(shots)
        if (shot := next((item for item in shots if item.id == shot_id), None)) is not None
        and ORIGINAL in shot.blobs
    ]
    draft_id = _draft_id(source_type, source_id, source_revision)
    existing = await repo.find_deconstruction(ctx.store, draft_id)
    if not cover_shot_id:
        if existing is not None and (
            existing.status is DeconstructionStatus.DRAFTED
            or (
                existing.status is DeconstructionStatus.NEEDS_COVER
                and existing.candidate_cover_shot_ids == candidates
            )
        ):
            return existing
        draft = Deconstruction(
            id=draft_id,
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            source_revision=source_revision,
            candidate_cover_shot_ids=candidates,
            input_digest=_digest(source),
        )
        await repo.put_deconstruction(ctx.store, draft)
        await _event(ctx, draft, "needs_cover")
        return draft
    if cover_shot_id not in candidates:
        raise DeconstructionConflict(
            "The cover must be a marked Keeper from this Deconstruction source"
        )

    analyses = await repo.list_analyses(ctx.store, user_id)
    member_ids = {shot.id for shot in shots}
    analyses = [analysis for analysis in analyses if analysis.shot_id in member_ids]
    if isinstance(source, ShootRecord):
        pages = rules.shoot_pages(source, shots, analyses, cover_shot_id)
        caption = (
            f"How I worked this Shoot: {source.receipt.shot_count} Shots across "
            f"{source.receipt.scene_count} Scenes."
        )
    else:
        pages = rules.experiment_pages(source, shots, cover_shot_id)
        caption = f"What I tried in {source.title}."
    digest = _digest({"source": source, "cover": cover_shot_id, "pages": pages})
    if (
        existing is not None
        and existing.status is DeconstructionStatus.DRAFTED
        and existing.input_digest == digest
        and all(page.blob_path for page in existing.pages)
    ):
        return existing

    prefix = deconstruction_blob_prefix(user_id, draft_id)
    await ctx.blobs.delete_prefix(prefix)
    try:
        for index, page in enumerate(pages, 1):
            images = []
            for shot_id in page.shot_ids:
                shot = next((item for item in shots if item.id == shot_id), None)
                if shot is None or ORIGINAL not in shot.blobs:
                    continue
                kind = ANNOTATED if page.visual_layer == "annotated" else ORIGINAL
                path = shot.blobs.get(kind) or shot.blobs[ORIGINAL]
                images.append(canvas.load_bytes(await ctx.blobs.read(path)))
            rendered = renderer.render(page, images, index, len(pages))
            path = deconstruction_blob_path(user_id, draft_id, index)
            await ctx.blobs.write(path, canvas.to_jpeg_bytes(rendered, quality=90), "image/jpeg")
            page.blob_path = path
    except Exception as exc:
        await ctx.blobs.delete_prefix(prefix)
        failed = Deconstruction(
            id=draft_id,
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            source_revision=source_revision,
            status=DeconstructionStatus.FAILED,
            candidate_cover_shot_ids=candidates,
            cover_shot_id=cover_shot_id,
            input_digest=digest,
            created_at=existing.created_at if existing else now(),
            updated_at=now(),
        )
        await repo.put_deconstruction(ctx.store, failed)
        await _event(ctx, failed, "failed")
        raise RuntimeError(f"Deconstruction rendering failed: {exc}") from exc

    drafted = Deconstruction(
        id=draft_id,
        user_id=user_id,
        source_type=source_type,
        source_id=source_id,
        source_revision=source_revision,
        status=DeconstructionStatus.DRAFTED,
        candidate_cover_shot_ids=candidates,
        cover_shot_id=cover_shot_id,
        pages=pages,
        suggested_caption=caption,
        input_digest=digest,
        created_at=existing.created_at if existing else now(),
        updated_at=now(),
    )
    await repo.put_deconstruction(ctx.store, drafted)
    await _event(ctx, drafted, "drafted")
    return drafted


async def _source(
    ctx: Context,
    user_id: str,
    source_type: DeconstructionSourceType,
    source_id: str,
    source_revision: int,
) -> tuple[ShootRecord | Experiment, list[Shot]]:
    if source_type is DeconstructionSourceType.SHOOT:
        if source_revision < 1:
            raise DeconstructionConflict("A settled Shoot revision is required")
        source = await repo.find_shoot_record(ctx.store, source_id, source_revision)
        if source is None or source.user_id != user_id:
            raise repo.UnknownEntity(f"Shoot Record {source_id} revision {source_revision}")
        shot_ids = source.shot_ids
    else:
        source = await repo.find_experiment(ctx.store, source_id)
        if source is None or source.user_id != user_id:
            raise repo.UnknownEntity(f"Experiment {source_id}")
        shot_ids = [source.reference_shot_id, *source.result_shot_ids]
    return source, await _shots(ctx, user_id, shot_ids)


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
        },
        experiment_id=(
            draft.source_id if draft.source_type is DeconstructionSourceType.EXPERIMENT else ""
        ),
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
