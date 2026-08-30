"""Drive selection, optional folder sync, and reviewed-copy export.

Google Picker selects existing files explicitly. ``/drive/connect`` is a
separate optional action that creates a Shoots folder and shares it with the
reader service account. Direct browser and Android ingress need neither.

``/drive/sync`` and ``/drive/notify`` are the same operation with different
callers: the dashboard button, and Google's push channel. Both just enqueue
unseen files; nothing else happens on the request path.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.agents import preflight as preflight_agent
from app.api.auth import current_user
from app.api.deps import get_context
from app.config import settings
from app.domain import taxonomy
from app.domain.entities import (
    Inspiration,
    Shot,
    ShotKind,
    ShotSource,
    SignalScope,
    SourceRole,
    User,
)
from app.imaging import canvas
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.infra.drive import DriveClient, DriveFile, UserDrive, picker_access_token, user_credentials
from app.infra.storage import ORIGINAL, blob_path, extension_for
from app.services import ingest, runs, source_authority, watch
from app.services.context import Context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drive", tags=["drive"])

LOCAL_FOLDER_ID = "local"


class ConnectResponse(BaseModel):
    folder_id: str
    folder_url: str
    reader: str
    mode: str


class SyncResponse(BaseModel):
    queued: int
    shot_ids: list[str]


class PickerConfigResponse(BaseModel):
    enabled: bool
    reason: str = ""
    api_key: str = ""
    app_id: str = ""
    oauth_token: str = ""
    max_files: int


class ImportRequest(BaseModel):
    file_ids: list[str]
    source_role: SourceRole = SourceRole.MINE


class ImportFailure(BaseModel):
    file_id: str
    name: str = ""
    error: str


class ImportResponse(BaseModel):
    discovered: int
    imported: int
    duplicates: int
    shot_ids: list[str]
    inspiration_ids: list[str]
    failures: list[ImportFailure]


async def _load_user(ctx: Context, session_user: dict) -> User:
    user = await repo.find_user(ctx.store, session_user["id"])
    if user is None:
        user = User(
            id=session_user["id"],
            email=session_user.get("email", ""),
            name=session_user.get("name", ""),
            picture=session_user.get("picture", ""),
        )
        await repo.put_user(ctx.store, user)
    return user


@router.post("/connect", response_model=ConnectResponse)
async def connect(session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)):
    user = await _load_user(ctx, session_user)

    if settings.drive_local_folder:
        # Local mode: the configured directory is the folder. Nothing to create.
        user.drive_folder_id = LOCAL_FOLDER_ID
        await repo.put_user(ctx.store, user)
        await repo.record(ctx.store, user.id, "drive", "connected", {"mode": "local"})
        return ConnectResponse(
            folder_id=LOCAL_FOLDER_ID,
            folder_url=settings.drive_local_folder,
            reader="local",
            mode="local",
        )

    if user.drive_folder_id:
        return ConnectResponse(
            folder_id=user.drive_folder_id,
            folder_url=_folder_url(user.drive_folder_id),
            reader=settings.drive_service_account,
            mode="google",
        )

    token = await ctx.tokens.get(user.id)
    if not token or not token.get("refresh_token"):
        raise HTTPException(
            409, "no Drive token for this user; sign out and sign in again to grant drive.file"
        )

    drive = UserDrive(user_credentials(token))
    folder_id = await drive.create_folder(settings.drive_folder_name)
    await drive.share_with(folder_id, settings.drive_service_account)

    user.drive_folder_id = folder_id
    await repo.put_user(ctx.store, user)
    await repo.record(
        ctx.store,
        user.id,
        "drive",
        "connected",
        {"folder_id": folder_id, "shared_with": settings.drive_service_account},
    )
    try:
        await watch.ensure(ctx, user)
    except Exception:  # polling still covers the folder; the daily tick retries
        logger.exception("could not open a Drive channel for %s", user.id)
    return ConnectResponse(
        folder_id=folder_id,
        folder_url=_folder_url(folder_id),
        reader=settings.drive_service_account,
        mode="google",
    )


@router.get("/picker-config", response_model=PickerConfigResponse)
async def picker_config(
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> PickerConfigResponse:
    if not settings.drive_picker_api_key or not settings.drive_picker_app_id:
        return PickerConfigResponse(
            enabled=False,
            reason="Google Drive selection is not configured on this server.",
            max_files=settings.drive_picker_max_files,
        )
    token = await ctx.tokens.get(session_user["id"]) if ctx.tokens else None
    if not token or not token.get("refresh_token"):
        return PickerConfigResponse(
            enabled=False,
            reason="Reconnect Google Drive to select existing files.",
            max_files=settings.drive_picker_max_files,
        )
    try:
        access_token = await picker_access_token(token)
    except Exception as error:
        logger.warning("Drive Picker token refresh failed for %s: %s", session_user["id"], error)
        return PickerConfigResponse(
            enabled=False,
            reason="Google Drive access expired. Reconnect Drive and try again.",
            max_files=settings.drive_picker_max_files,
        )
    return PickerConfigResponse(
        enabled=True,
        api_key=settings.drive_picker_api_key,
        app_id=settings.drive_picker_app_id,
        oauth_token=access_token,
        max_files=settings.drive_picker_max_files,
    )


def _selected_drive(ctx: Context, user_id: str, token: dict | None) -> DriveClient | UserDrive:
    if settings.drive_local_folder:
        if ctx.drive is None:
            raise HTTPException(503, "Local Drive adapter is unavailable")
        return ctx.drive
    if not token or not token.get("refresh_token"):
        raise HTTPException(409, "Connect Google Drive before selecting existing files")
    return UserDrive(user_credentials(token))


@router.post("/import", response_model=ImportResponse)
async def import_files(
    body: ImportRequest,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> ImportResponse:
    """Accept only explicitly selected Drive ids, then enter the normal pipeline."""
    user = await _load_user(ctx, session_user)
    file_ids = list(dict.fromkeys(value.strip() for value in body.file_ids if value.strip()))
    if not file_ids:
        raise HTTPException(400, "select at least one Drive file")
    if len(file_ids) > settings.drive_picker_max_files:
        raise HTTPException(413, f"select at most {settings.drive_picker_max_files} files")
    token = await ctx.tokens.get(user.id) if ctx.tokens else None
    drive = _selected_drive(ctx, user.id, token)

    created_shots: list[str] = []
    created_inspirations: list[str] = []
    duplicates = 0
    failures: list[ImportFailure] = []
    for file_id in file_ids:
        name = ""
        try:
            selected = await drive.get_file(file_id)
            name = selected.name
            if not selected.is_media:
                raise ValueError("only image and video files can be imported")
            if selected.size > settings.max_upload_bytes:
                raise ValueError("file is larger than the upload limit")
            record_id = (
                repo.shot_id_for(user.id, selected.id)
                if body.source_role is SourceRole.MINE
                else repo.source_inspiration_id_for(
                    user.id,
                    ShotSource.DRIVE_PICKER.value,
                    selected.id,
                )
            )
            if body.source_role is SourceRole.MINE:
                existing_inspiration = await repo.find_inspiration(
                    ctx.store,
                    repo.source_inspiration_id_for(
                        user.id,
                        ShotSource.DRIVE_PICKER.value,
                        selected.id,
                    ),
                )
                if existing_inspiration is not None and not existing_inspiration.superseded_at:
                    raise ValueError("this Drive file is already Inspiration")
                existing = await repo.find_shot(ctx.store, record_id)
                if existing is not None:
                    duplicates += 1
                    await runs.ensure(ctx, existing)
                    await ingest.resume(ctx, existing)
                    continue
            else:
                existing_mine = await repo.find_shot(
                    ctx.store,
                    repo.shot_id_for(user.id, selected.id),
                )
                if existing_mine is not None and not existing_mine.superseded_at:
                    raise ValueError("this Drive file is already in the archive as Mine")
                existing_inspiration = await repo.find_inspiration(ctx.store, record_id)
                if existing_inspiration is not None and not existing_inspiration.superseded_at:
                    duplicates += 1
                    continue

            data = await drive.download(selected.id)
            if not data:
                raise ValueError("selected file is empty")
            if len(data) > settings.max_upload_bytes:
                raise ValueError("file is larger than the upload limit")
            original = blob_path(
                user.id,
                record_id,
                ORIGINAL,
                extension_for(selected.mime_type),
            )
            original = await ctx.blobs.write(original, data, selected.mime_type)

            if body.source_role is SourceRole.INSPIRATION:
                inspiration = Inspiration(
                    id=record_id,
                    user_id=user.id,
                    source=ShotSource.DRIVE_PICKER,
                    source_id=selected.id,
                    filename=selected.name,
                    mime_type=selected.mime_type,
                    blobs={ORIGINAL: original},
                )
                await repo.put_inspiration(ctx.store, inspiration)
                await source_authority.record_source_role(
                    ctx,
                    user.id,
                    SignalScope.INSPIRATION,
                    inspiration.id,
                    SourceRole.INSPIRATION.value,
                )
                created_inspirations.append(inspiration.id)
                continue

            shot = Shot(
                id=record_id,
                user_id=user.id,
                kind=(
                    ShotKind.VIDEO if selected.mime_type.startswith("video/") else ShotKind.PHOTO
                ),
                source=ShotSource.DRIVE_PICKER,
                source_id=selected.id,
                drive_file_id=selected.id,
                filename=selected.name,
                mime_type=selected.mime_type,
                blobs={ORIGINAL: original},
            )
            await repo.put_shot(ctx.store, shot)
            await source_authority.record_source_role(
                ctx,
                user.id,
                SignalScope.SHOT,
                shot.id,
                SourceRole.MINE.value,
            )
            await runs.ensure(ctx, shot)
            await repo.record(
                ctx.store,
                user.id,
                "ingest",
                "queued",
                {
                    "filename": selected.name,
                    "via": ShotSource.DRIVE_PICKER.value,
                    "source_role": SourceRole.MINE.value,
                },
                shot_id=shot.id,
            )
            await ctx.bus.publish(TOPICS["media.new"], {"shot_id": shot.id})
            created_shots.append(shot.id)
        except Exception as error:
            failures.append(
                ImportFailure(
                    file_id=file_id,
                    name=name,
                    error=f"{type(error).__name__}: {error}"[:300],
                )
            )

    await repo.record(
        ctx.store,
        user.id,
        "drive",
        "imported",
        {
            "discovered": len(file_ids),
            "imported": len(created_shots) + len(created_inspirations),
            "duplicates": duplicates,
            "failed": len(failures),
            "source_role": body.source_role.value,
        },
    )
    return ImportResponse(
        discovered=len(file_ids),
        imported=len(created_shots) + len(created_inspirations),
        duplicates=duplicates,
        shot_ids=created_shots,
        inspiration_ids=created_inspirations,
        failures=failures,
    )


@router.post("/sync", response_model=SyncResponse)
async def sync(session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)):
    user = await _load_user(ctx, session_user)
    if not user.drive_folder_id:
        raise HTTPException(409, "connect a Drive folder first")
    shots = await ingest.sync(ctx, user)
    return SyncResponse(queued=len(shots), shot_ids=[s.id for s in shots])


@router.post("/notify", status_code=204)
async def notify(
    request: Request,
    ctx: Context = Depends(get_context),
    channel_token: str | None = Header(default=None, alias="X-Goog-Channel-Token"),
    channel_id: str | None = Header(default=None, alias="X-Goog-Channel-ID"),
    resource_state: str | None = Header(default=None, alias="X-Goog-Resource-State"),
):
    """Drive push notification (services/watch.py). The channel token is the
    user id we set when the channel was opened and the channel id must be the
    one we hold, so a stale or forged channel cannot make us do anything; and
    all it could make us do is list the folder."""
    if resource_state == "sync":
        return None  # the hello message Drive sends when a channel opens
    if not channel_token:
        raise HTTPException(400, "missing channel token")
    user = await repo.find_user(ctx.store, channel_token)
    if user is None or not user.drive_channel or user.drive_channel.channel_id != channel_id:
        logger.warning("drive notify for unknown user or channel")
        return None
    await ingest.sync(ctx, user)
    return None


class ShootResponse(BaseModel):
    shot_id: str
    drive_file_id: str
    experiment_id: str


@router.post("/shoot", response_model=ShootResponse)
async def shoot(
    file: UploadFile = File(...),
    experiment_id: str = Form(default=""),
    pitch_deg: float | None = Form(default=None),
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    """The Shoot button, from the web app or from the native camera.

    The file goes to the user's Drive folder, so the folder stays the single
    source of truth; the shot is tagged with the experiment it answers; and the
    pipeline starts now rather than at the next sync.

    ``pitch_deg`` only ever arrives from the native camera. It is the one fact
    no photograph carries - how far from level the camera was aimed - and it is
    what closes the height blind spot in the Tendency Profile.
    """
    user = await _load_user(ctx, session_user)
    if not user.drive_folder_id:
        raise HTTPException(409, "connect a Drive folder first")
    mime = file.content_type or "application/octet-stream"
    if not mime.startswith(("image/", "video/")):
        raise HTTPException(415, "image and video files only")
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "file too large")
    name = Path(file.filename or "shot").name

    if settings.drive_local_folder:
        target = Path(settings.drive_local_folder) / name
        target.write_bytes(data)
        files = await ctx.drive.list_media(user.drive_folder_id)
        match = next((f for f in files if f.name == name), None)
        if match is None:
            raise HTTPException(500, "local upload did not appear in the folder")
        drive_file = match
    else:
        token = await ctx.tokens.get(user.id)
        if not token or not token.get("refresh_token"):
            raise HTTPException(409, "no Drive token; sign out and in again")
        file_id = await UserDrive(user_credentials(token)).upload(
            user.drive_folder_id, name, data, mime
        )
        drive_file = DriveFile(
            id=file_id, name=name, mime_type=mime, size=len(data), modified_at=_now()
        )

    shot_id = repo.shot_id_for(user.id, drive_file.id)
    existing = await repo.find_shot(ctx.store, shot_id)
    if existing is None:
        shot = ingest.new_shot(shot_id, user.id, drive_file, experiment_id=experiment_id)
        shot.pitch_deg = pitch_deg
        await repo.put_shot(ctx.store, shot)
        await runs.ensure(ctx, shot)
        await repo.record(
            ctx.store,
            user.id,
            "ingest",
            "queued",
            {"filename": name, "via": "shoot"},
            shot_id=shot_id,
        )
        await ctx.bus.publish(TOPICS["media.new"], {"shot_id": shot_id})
    return ShootResponse(shot_id=shot_id, drive_file_id=drive_file.id, experiment_id=experiment_id)


class PreflightCheck(BaseModel):
    criterion: str
    met: bool
    fix: str = ""


class PreflightResponse(BaseModel):
    ready: bool
    say: str
    checks: list[PreflightCheck]
    seconds: float


@router.post("/preflight", response_model=PreflightResponse)
async def preflight(
    file: UploadFile = File(...),
    experiment_id: str = Form(...),
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    """Explicit Ask: visible Criteria checked on a temporary Scene Probe.

    No Shot or image blob is created. Only the ActivityEvent below survives.
    """
    import time

    user = await _load_user(ctx, session_user)
    experiment = await repo.get_experiment(ctx.store, experiment_id)
    if experiment.user_id != user.id:
        raise HTTPException(404, "experiment not found")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(415, "image files only; videos go straight to the pipeline")
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "file too large")
    preview = canvas.fit_for_model(canvas.load_bytes(data), preflight_agent.PREVIEW_EDGE)
    started = time.monotonic()
    out = await preflight_agent.check(
        experiment, taxonomy.get(experiment.technique_id), canvas.to_jpeg_bytes(preview, quality=80)
    )
    seconds = round(time.monotonic() - started, 1)
    await repo.record(
        ctx.store,
        user.id,
        "judge",
        "preflight",
        {
            "ready": out.ready,
            "say": out.say,
            "unmet": [c.criterion for c in out.checks if not c.met],
            "seconds": seconds,
        },
        experiment_id=experiment.id,
    )
    return PreflightResponse(
        ready=out.ready,
        say=out.say,
        checks=[PreflightCheck(criterion=c.criterion, met=c.met, fix=c.fix) for c in out.checks],
        seconds=seconds,
    )


def _now():
    from app.domain.entities import now

    return now()


def _folder_url(folder_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{folder_id}"
