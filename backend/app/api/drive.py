"""Drive: connect a folder, sync it, and receive change notifications.

``/drive/connect`` is the one thing the user does once. As the user (their
``drive.file`` token) the app creates the Shoots folder and shares it with the
reader service account. From then on the reader sees whatever lands there.

``/drive/sync`` and ``/drive/notify`` are the same operation with different
callers: the dashboard button, and Google's push channel. Both just enqueue
unseen files; nothing else happens on the request path.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from app.api.auth import current_user
from app.api.deps import get_context
from app.config import settings
from app.domain.entities import User
from app.infra import repository as repo
from app.infra.drive import UserDrive, user_credentials
from app.services import ingest
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
    resource_state: str | None = Header(default=None, alias="X-Goog-Resource-State"),
):
    """Drive push notification. The channel token is the user id we set when
    the channel was opened; ``sync`` is the only thing we do with it."""
    if resource_state == "sync":
        return None  # the hello message Drive sends when a channel opens
    if not channel_token:
        raise HTTPException(400, "missing channel token")
    user = await repo.find_user(ctx.store, channel_token)
    if user is None:
        logger.warning("drive notify for unknown user token")
        return None
    await ingest.sync(ctx, user)
    return None


def _folder_url(folder_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{folder_id}"
