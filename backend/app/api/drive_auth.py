"""Optional native Drive authorization, separate from Google sign-in."""

import asyncio

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.api.auth import current_user
from app.api.deps import get_context
from app.api.drive import ConnectResponse, connect
from app.config import settings
from app.infra import repository as repo
from app.infra.drive import UserDrive, user_credentials
from app.services.context import Context

router = APIRouter(prefix="/api/drive", tags=["drive-authorization"])


class AuthorizationCodeIn(BaseModel):
    code: str = Field(min_length=8, max_length=4096)


async def exchange_drive_code(body: AuthorizationCodeIn) -> dict:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(500, "Google OAuth server credentials are not configured")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": body.code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "grant_type": "authorization_code",
                "redirect_uri": "",
            },
        )
    if response.status_code != 200:
        raise HTTPException(401, "Google Drive authorization code was rejected")
    token = response.json()
    encoded_id = token.get("id_token", "")
    if not encoded_id:
        access_token = token.get("access_token", "")
        if not access_token:
            raise HTTPException(401, "Google returned no identity with Drive authorization")
        async with httpx.AsyncClient(timeout=20) as client:
            identity = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if identity.status_code != 200 or not identity.json().get("sub"):
            raise HTTPException(401, "Google Drive identity could not be verified")
        return {"token": token, "claims": identity.json()}

    def verify() -> dict:
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2 import id_token

        return id_token.verify_oauth2_token(
            encoded_id,
            GoogleRequest(),
            settings.google_client_id,
        )

    try:
        claims = await asyncio.to_thread(verify)
    except ValueError as exc:
        raise HTTPException(401, "Google Drive identity is invalid") from exc
    return {"token": token, "claims": claims}


@router.post("/authorization-code", response_model=ConnectResponse)
async def authorize_drive(
    body: AuthorizationCodeIn,
    exchanged: dict = Depends(exchange_drive_code),
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> ConnectResponse:
    if exchanged["claims"].get("sub") != session_user["id"]:
        raise HTTPException(409, "Drive was authorized with a different Google account")
    token = exchanged["token"]
    existing = await ctx.tokens.get(session_user["id"]) or {}
    refresh_token = token.get("refresh_token") or existing.get("refresh_token", "")
    if not refresh_token:
        raise HTTPException(409, "Google returned no offline Drive access")
    await ctx.tokens.put(
        session_user["id"],
        {
            "refresh_token": refresh_token,
            "access_token": token.get("access_token", ""),
            "scope": token.get("scope", ""),
        },
    )
    return await connect(session_user, ctx)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_drive(
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Response:
    user = await repo.get_user(ctx.store, session_user["id"])
    if user.drive_channel and ctx.drive is not None:
        await ctx.drive.stop(user.drive_channel.channel_id, user.drive_channel.resource_id)
    token = await ctx.tokens.get(user.id)
    if (
        user.drive_folder_id
        and user.drive_folder_id != "local"
        and token
        and settings.drive_service_account
    ):
        await UserDrive(user_credentials(token)).unshare_with(
            user.drive_folder_id, settings.drive_service_account
        )
    await ctx.tokens.delete(user.id)
    user.drive_folder_id = ""
    user.drive_channel = None
    user.drive_page_token = ""
    user.drive_review_folder_id = ""
    await repo.put_user(ctx.store, user)
    await repo.record(ctx.store, user.id, "drive", "disconnected", {})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
