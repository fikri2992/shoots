"""Native Android identity, notification target, and device revocation."""

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.api import auth
from app.api.auth import current_user
from app.api.deps import get_context
from app.api.pairing import token_fingerprint
from app.domain.entities import CameraCapabilities, User, now
from app.infra import repository as repo
from app.services.context import Context

router = APIRouter(tags=["devices"])


class NotificationTargetIn(BaseModel):
    target: str = Field(default="", max_length=512)


@router.put("/api/devices/current/camera-capabilities", status_code=204)
async def set_camera_capabilities(
    body: CameraCapabilities,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Response:
    device_id = session_user.get("device_id", "")
    if not device_id:
        raise HTTPException(409, "A native device session is required")
    device = await repo.find_device(ctx.store, device_id)
    if device is None or device["user_id"] != session_user["id"]:
        raise HTTPException(404, "Device session not found")
    await repo.set_device_camera_capabilities(ctx.store, device_id, body)
    return Response(status_code=204)


@router.post(
    "/auth/android/session",
    response_model=auth.AndroidSessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def android_session(
    body: auth.AndroidSessionIn,
    claims: dict = Depends(auth.verify_android_token),
    ctx: Context = Depends(get_context),
) -> auth.AndroidSessionOut:
    user = await repo.find_user(ctx.store, claims["sub"]) or User(
        id=claims["sub"], email=claims["email"]
    )
    user.email = claims["email"]
    user.name = claims.get("name", "") or user.name
    user.picture = claims.get("picture", "") or user.picture
    await repo.put_user(ctx.store, user)

    token = secrets.token_urlsafe(32)
    expires_at = now() + timedelta(days=30)
    await repo.put_device(
        ctx.store,
        token_fingerprint(token),
        user.id,
        body.device.strip()[:60] or "Android",
        expires_at=expires_at,
        auth_method="google",
    )
    await repo.record(
        ctx.store,
        user.id,
        "identity",
        "device_signed_in",
        {"device": body.device.strip()[:60] or "Android"},
    )
    return auth.AndroidSessionOut(token=token, expires_at=expires_at, user=user)


@router.delete("/api/devices/current", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_current_device(
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Response:
    device_id = session_user.get("device_id", "")
    if not device_id:
        raise HTTPException(409, "The current session is not a revocable device session")
    await repo.record(
        ctx.store,
        session_user["id"],
        "identity",
        "device_revoked",
        {"device": session_user.get("device", "Android")},
    )
    await repo.delete_device(ctx.store, device_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/api/devices/current/notifications",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def set_notifications(
    body: NotificationTargetIn,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Response:
    device_id = session_user.get("device_id", "")
    if not device_id:
        raise HTTPException(409, "The current session is not a native device session")
    if not await repo.set_device_notification_target(ctx.store, device_id, body.target.strip()):
        raise HTTPException(404, "Device session not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
