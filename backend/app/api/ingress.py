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
    Shot,
    ShotKind,
    ShotSource,
)
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.infra.storage import ORIGINAL, blob_path, extension_for
from app.services import ingest, runs, shoots
from app.services.context import Context

router = APIRouter(prefix="/api/ingress", tags=["ingress"])


class IngressResponse(BaseModel):
    shot_id: str
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
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> IngressResponse:
    """Accept one original from the Android Phone Source.

    ``source_id`` comes from Android MediaStore and device identity. It is the
    idempotency key, so WorkManager may retry the upload after any ambiguous
    network failure without creating another Shot.
    """
    mime = (file.content_type or "application/octet-stream").split(";", 1)[0].lower()
    if not mime.startswith(("image/", "video/")):
        raise HTTPException(415, "image and video files only")
    user_id = session_user["id"]
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

    shot_id = repo.source_shot_id_for(user_id, ShotSource.ANDROID.value, source_id)
    existing = await repo.find_shot(ctx.store, shot_id)
    if existing is not None:
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
            source_id=existing.source_id or source_id,
            experiment_id=existing.experiment_id,
            capture_session_id=existing.capture_session_id,
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

    name = Path(file.filename or "shot").name
    original = blob_path(user_id, shot_id, ORIGINAL, extension_for(mime))
    await ctx.blobs.write_file(original, file.file, mime)
    shot = Shot(
        id=shot_id,
        user_id=user_id,
        kind=ShotKind.VIDEO if mime.startswith("video/") else ShotKind.PHOTO,
        source=ShotSource.ANDROID,
        source_id=source_id,
        filename=name,
        mime_type=mime,
        blobs={ORIGINAL: original},
        experiment_id=experiment_id,
        capture_session_id=capture_session_id,
    )
    await repo.put_shot(ctx.store, shot)
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
            "via": "android",
            "source": ShotSource.ANDROID.value,
            "capture_session_id": capture_session_id,
        },
        shot_id=shot.id,
        experiment_id=experiment_id,
    )
    await ctx.bus.publish(TOPICS["media.new"], {"shot_id": shot.id})
    return IngressResponse(
        shot_id=shot.id,
        source_id=source_id,
        experiment_id=experiment_id,
        capture_session_id=capture_session_id,
        created=True,
    )
