"""Authenticated, idempotent Shot ingress independent of Google Drive."""

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.auth import current_user
from app.api.deps import get_context
from app.config import settings
from app.domain.entities import (
    CaptureSessionStatus,
    ExperimentStatus,
    ExperimentType,
    Inspiration,
    Shot,
    ShotKind,
    ShotSource,
    SignalScope,
    SourceRole,
)
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.infra.storage import ORIGINAL, blob_path, extension_for
from app.services import ingest, runs, shoots, source_authority
from app.services.context import Context

router = APIRouter(prefix="/api/ingress", tags=["ingress"])


class IngressResponse(BaseModel):
    shot_id: str = ""
    inspiration_id: str = ""
    source_role: SourceRole = SourceRole.MINE
    source_id: str
    experiment_id: str
    capture_session_id: str
    created: bool


@router.post("/shots", response_model=IngressResponse)
async def receive_shot(
    file: UploadFile = File(...),
    source_id: str = Form(..., min_length=1, max_length=300),
    experiment_id: str = Form(default=""),
    capture_session_id: str = Form(default=""),
    source_role: SourceRole | None = Form(default=None),
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> IngressResponse:
    """Accept one original from Android or a browser upload.

    ``source_id`` comes from Android MediaStore and device identity. It is the
    idempotency key, so WorkManager may retry the upload after any ambiguous
    network failure without creating another Shot.
    """
    mime = (file.content_type or "application/octet-stream").split(";", 1)[0].lower()
    if not mime.startswith(("image/", "video/")):
        raise HTTPException(415, "image and video files only")
    user_id = session_user["id"]
    automatic_camera = ":external:" in source_id
    if source_role is SourceRole.INSPIRATION and (
        automatic_camera or capture_session_id or experiment_id
    ):
        raise HTTPException(409, "Camera and Experiment media are Mine by source contract")
    resolved_role = source_role or SourceRole.MINE
    role_basis = (
        "explicit"
        if source_role is not None
        else "camera_contract"
        if automatic_camera or capture_session_id
        else "legacy_default"
    )
    variation_id = ""
    if capture_session_id:
        capture_session = await repo.find_capture_session(ctx.store, capture_session_id)
        if capture_session is None or capture_session.user_id != user_id:
            raise HTTPException(404, "Capture Session not found")
        if capture_session.status not in {
            CaptureSessionStatus.COMMITTED,
            CaptureSessionStatus.PROCESSING,
        }:
            raise HTTPException(409, "Capture Session is not accepting members")
        if not any(member.source_id == source_id for member in capture_session.members):
            raise HTTPException(409, "Shot is not in the committed Capture Session manifest")
        experiment_id = capture_session.experiment_id
        variation_id = capture_session.variation_id

    source = (
        ShotSource.ANDROID
        if session_user.get("device") or automatic_camera
        else ShotSource.WEB_UPLOAD
    )
    shot_id = repo.source_shot_id_for(user_id, source.value, source_id)
    inspiration_id = repo.source_inspiration_id_for(
        user_id,
        source.value,
        source_id,
    )
    existing = await repo.find_shot(ctx.store, shot_id)
    if existing is not None:
        if resolved_role is SourceRole.INSPIRATION:
            raise HTTPException(409, "This source was already accepted as Mine")
        if existing.superseded_by_inspiration_id:
            raise HTTPException(
                409,
                "This source is currently Inspiration; correct its role explicitly",
            )
        if capture_session_id and existing.capture_session_id != capture_session_id:
            raise HTTPException(409, "Shot was already accepted outside this Capture Session")
        # The first accepted write owns the Experiment association. A retry
        # after that Experiment closed must still succeed, never reinterpret
        # the same media as a different result. Resume from durable state in
        # case the previous request committed the Shot but lost its publish.
        await runs.ensure(ctx, existing)
        await shoots.observe_shot(ctx, existing.id)
        if capture_session_id:
            await repo.accept_capture_session_member(
                ctx.store, capture_session_id, source_id, existing.id
            )
        await ingest.resume(ctx, existing)
        return IngressResponse(
            shot_id=existing.id,
            source_role=SourceRole.MINE,
            source_id=existing.source_id or source_id,
            experiment_id=existing.experiment_id,
            capture_session_id=existing.capture_session_id,
            created=False,
        )
    existing_inspiration = await repo.find_inspiration(ctx.store, inspiration_id)
    if existing_inspiration is not None and not existing_inspiration.superseded_at:
        if resolved_role is SourceRole.MINE:
            raise HTTPException(409, "This source was already accepted as Inspiration")
        return IngressResponse(
            inspiration_id=existing_inspiration.id,
            source_role=SourceRole.INSPIRATION,
            source_id=existing_inspiration.source_id,
            experiment_id="",
            capture_session_id="",
            created=False,
        )

    def size_and_rewind() -> int:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        return size

    size = await asyncio.to_thread(size_and_rewind)
    if size > settings.max_upload_bytes:
        raise HTTPException(413, "file too large")
    if not size:
        raise HTTPException(400, "empty file")

    if experiment_id:
        experiment = await repo.find_experiment(ctx.store, experiment_id)
        if (
            experiment is None
            or experiment.user_id != user_id
            or experiment.status is not ExperimentStatus.OPEN
        ):
            raise HTTPException(409, "Experiment is not open for this photographer")
        if experiment.type is ExperimentType.EXPLORE and not capture_session_id:
            raise HTTPException(409, "Explore results require a Variation Capture Session")

    name = Path(file.filename or "shot").name
    record_id = inspiration_id if resolved_role is SourceRole.INSPIRATION else shot_id
    original = blob_path(user_id, record_id, ORIGINAL, extension_for(mime))
    await ctx.blobs.write_file(original, file.file, mime)
    if resolved_role is SourceRole.INSPIRATION:
        inspiration = Inspiration(
            id=inspiration_id,
            user_id=user_id,
            source=source,
            source_id=source_id,
            filename=name,
            mime_type=mime,
            blobs={ORIGINAL: original},
        )
        await repo.put_inspiration(ctx.store, inspiration)
        await source_authority.record_source_role(
            ctx,
            user_id,
            SignalScope.INSPIRATION,
            inspiration.id,
            SourceRole.INSPIRATION.value,
        )
        await repo.record(
            ctx.store,
            user_id,
            "ingest",
            "inspiration_accepted",
            {"filename": name, "via": source.value, "role_basis": role_basis},
        )
        return IngressResponse(
            inspiration_id=inspiration.id,
            source_role=SourceRole.INSPIRATION,
            source_id=source_id,
            experiment_id="",
            capture_session_id="",
            created=True,
        )
    shot = Shot(
        id=shot_id,
        user_id=user_id,
        kind=ShotKind.VIDEO if mime.startswith("video/") else ShotKind.PHOTO,
        source=source,
        source_id=source_id,
        filename=name,
        mime_type=mime,
        blobs={ORIGINAL: original},
        experiment_id=experiment_id,
        variation_id=variation_id,
        capture_session_id=capture_session_id,
    )
    await repo.put_shot(ctx.store, shot)
    if source_role is not None and not automatic_camera and not capture_session_id:
        await source_authority.record_source_role(
            ctx,
            user_id,
            SignalScope.SHOT,
            shot.id,
            SourceRole.MINE.value,
        )
    await runs.ensure(ctx, shot)
    await shoots.observe_shot(ctx, shot.id)
    if capture_session_id:
        await repo.accept_capture_session_member(ctx.store, capture_session_id, source_id, shot.id)
    await repo.record(
        ctx.store,
        user_id,
        "ingest",
        "queued",
        {
            "filename": name,
            "via": source.value,
            "source": source.value,
            "capture_session_id": capture_session_id,
            "source_role": SourceRole.MINE.value,
            "role_basis": role_basis,
        },
        shot_id=shot.id,
        experiment_id=experiment_id,
    )
    await ctx.bus.publish(TOPICS["media.new"], {"shot_id": shot.id})
    return IngressResponse(
        shot_id=shot.id,
        source_role=SourceRole.MINE,
        source_id=source_id,
        experiment_id=experiment_id,
        capture_session_id=capture_session_id,
        created=True,
    )
