"""Web Push subscriptions for the PWA."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import current_user
from app.api.deps import get_context
from app.config import settings
from app.services import notify
from app.services.context import Context

router = APIRouter(prefix="/api/push", tags=["push"])


class Subscription(BaseModel):
    endpoint: str
    keys: dict[str, str]
    expirationTime: int | None = None  # noqa: N815 — the browser's field name


class Unsubscribe(BaseModel):
    endpoint: str


@router.get("/key")
async def public_key():
    return {"key": settings.vapid_public_key, "enabled": bool(settings.vapid_private_key)}


@router.post("/subscribe", status_code=201)
async def subscribe(
    body: Subscription,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    try:
        sid = await notify.subscribe(ctx.store, session_user["id"], body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"id": sid}


@router.delete("/subscribe", status_code=204)
async def unsubscribe(
    body: Unsubscribe,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    await notify.unsubscribe(ctx.store, session_user["id"], body.endpoint)
    return None


@router.post("/test")
async def test_push(
    session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)
):
    """Sends one notification to the caller's devices, so the setup can be checked."""
    delivered = await notify.notify(
        ctx, session_user["id"], "Shoots", "Notifications are on.", url="/", tag="test"
    )
    return {"delivered": delivered}
