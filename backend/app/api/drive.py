"""Drive: connect a folder, sync it, and receive change notifications.

``/drive/connect`` is the one thing the user does once. As the user (their
``drive.file`` token) the app creates the Shoots folder and shares it with the
reader service account. From then on the reader sees whatever lands there.

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
from app.domain.entities import User
from app.imaging import canvas
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.infra.drive import DriveFile, UserDrive, user_credentials
from app.services import ingest, watch
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
    quest_id: str


MAX_UPLOAD_BYTES = 200 * 1024 * 1024


@router.post("/shoot", response_model=ShootResponse)
async def shoot(
    file: UploadFile = File(...),
    quest_id: str = Form(default=""),
    pitch_deg: float | None = Form(default=None),
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    """The Shoot button, from the web app or from the native camera.

    The file goes to the user's Drive folder, so the folder stays the single
    source of truth; the shot is tagged with the quest it answers; and the
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
        raise HTTPException(415, "photos and videos only")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
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
        shot = ingest.new_shot(shot_id, user.id, drive_file, quest_id=quest_id)
        shot.pitch_deg = pitch_deg
        await repo.put_shot(ctx.store, shot)
        await repo.record(
            ctx.store,
            user.id,
            "ingest",
            "queued",
            {"filename": name, "via": "shoot"},
            shot_id=shot_id,
        )
        await ctx.bus.publish(TOPICS["media.new"], {"shot_id": shot_id})
    return ShootResponse(shot_id=shot_id, drive_file_id=drive_file.id, quest_id=quest_id)


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
    quest_id: str = Form(...),
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    """On location, before upload: the quest's criteria checked on a preview
    in a few seconds, so a miss is reshot now rather than judged later."""
    import time

    user = await _load_user(ctx, session_user)
    quest = await repo.get_quest(ctx.store, quest_id)
    if quest.user_id != user.id:
        raise HTTPException(404, "quest not found")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(415, "photos only; videos go straight to the pipeline")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "file too large")
    preview = canvas.fit_for_model(canvas.load_bytes(data), preflight_agent.PREVIEW_EDGE)
    started = time.monotonic()
    out = await preflight_agent.check(
        quest, taxonomy.get(quest.technique_id), canvas.to_jpeg_bytes(preview, quality=80)
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
        quest_id=quest.id,
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
