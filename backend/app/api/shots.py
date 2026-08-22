"""Read side for the dashboard: shots, events, blobs. Signed-in user only."""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.api.auth import current_user
from app.api.deps import get_context
from app.domain.entities import ActivityEvent, Analysis, Shot, User
from app.infra import repository as repo
from app.infra.storage import user_prefix
from app.services.context import Context

router = APIRouter(prefix="/api", tags=["shots"])

_CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "mp4": "video/mp4",
    "bin": "application/octet-stream",
}


@router.get("/me", response_model=User | None)
async def me(session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)):
    return await repo.find_user(ctx.store, session_user["id"])


class ShotView(BaseModel):
    shot: Shot
    analysis: Analysis | None = None


@router.get("/shots", response_model=list[ShotView])
async def list_shots(
    limit: int = 100,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    shots = await repo.list_shots(ctx.store, session_user["id"], limit=limit)
    views = []
    for shot in shots:
        analysis = await repo.find_analysis(ctx.store, shot.id) if shot.analyzed_at else None
        views.append(ShotView(shot=shot, analysis=analysis))
    return views


@router.get("/shots/{shot_id}", response_model=ShotView)
async def get_shot(
    shot_id: str, session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)
):
    shot = await repo.find_shot(ctx.store, shot_id)
    if shot is None or shot.user_id != session_user["id"]:
        raise HTTPException(404, "shot not found")
    return ShotView(shot=shot, analysis=await repo.find_analysis(ctx.store, shot.id))


@router.get("/events", response_model=list[ActivityEvent])
async def list_events(
    limit: int = 100,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    return await repo.list_events(ctx.store, session_user["id"], limit=limit)


@router.get("/blobs/{path:path}")
async def blob(
    path: str, session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)
):
    """Blobs are namespaced by user id; the prefix check is the whole ACL."""
    if not path.startswith(user_prefix(session_user["id"])) or ".." in path:
        raise HTTPException(404, "not found")
    if not await ctx.blobs.exists(path):
        raise HTTPException(404, "not found")
    data = await ctx.blobs.read(path)
    extension = path.rsplit(".", 1)[-1].lower()
    return Response(
        data,
        media_type=_CONTENT_TYPES.get(extension, "application/octet-stream"),
        headers={"Cache-Control": "private, max-age=3600"},
    )
