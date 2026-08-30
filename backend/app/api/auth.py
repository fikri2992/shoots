"""Google identity for web sessions and native Android device sessions."""

import asyncio
from datetime import datetime

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.api.deps import get_context
from app.config import settings
from app.domain.entities import RecordMode, User, now
from app.infra import repository as repo
from app.services.context import Context

router = APIRouter(prefix="/auth", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": settings.oauth_scopes},
    # Refresh token only comes back with offline access on a consent screen.
    # These must be authorize params; client_kwargs does not reach the URL.
    authorize_params={"access_type": "offline", "prompt": "consent"},
)

SESSION_USER_KEY = "user"


@router.get("/login")
async def login(request: Request):
    if not settings.google_client_id:
        raise HTTPException(500, "GOOGLE_CLIENT_ID is not configured")
    return await oauth.google.authorize_redirect(request, settings.oauth_redirect_uri)


@router.get("/callback")
async def callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as exc:
        raise HTTPException(401, f"OAuth failed: {exc.error}") from exc

    claims = token.get("userinfo") or {}
    if not claims.get("email"):
        raise HTTPException(401, "Google returned no email")

    session_user = {
        "id": claims["sub"],
        "email": claims["email"],
        "name": claims.get("name", ""),
        "picture": claims.get("picture", ""),
    }
    request.session[SESSION_USER_KEY] = session_user
    await _remember(session_user, token)
    return RedirectResponse(settings.frontend_origin)


async def _remember(session_user: dict, token: dict | None) -> None:
    """Upsert the user record; keep the Drive refresh token out of Firestore.

    Google only returns a refresh token on the consent screen (prompt=consent),
    which we force, so a fresh sign-in always carries one. A token without it
    is not stored: it could not refresh, so it would only mislead Connect.
    """
    from app.api.deps import get_context

    ctx = get_context()
    existing = await repo.find_user(ctx.store, session_user["id"])
    user = existing or User(id=session_user["id"], email=session_user["email"])
    user.name = session_user.get("name", "") or user.name
    user.picture = session_user.get("picture", "") or user.picture
    await repo.put_user(ctx.store, user)

    if token and token.get("refresh_token"):
        await ctx.tokens.put(
            user.id,
            {
                "refresh_token": token["refresh_token"],
                "access_token": token.get("access_token", ""),
                "scope": token.get("scope", ""),
            },
        )


@router.get("/me")
async def me(request: Request):
    user = request.session.get(SESSION_USER_KEY)
    if not user:
        raise HTTPException(401, "not signed in")
    return user


@router.post("/logout")
async def logout(request: Request):
    request.session.pop(SESSION_USER_KEY, None)
    return JSONResponse({"ok": True})


class DevLogin(BaseModel):
    email: str
    name: str = ""


@router.post("/dev-login")
async def dev_login(body: DevLogin, request: Request):
    """Sign in without Google, for local development only.

    Guarded by ``settings.dev_login_allowed``, which requires an explicit opt-in flag
    AND the absence of any real cloud configuration. It exists so the app can be run
    and reviewed from a fresh clone before OAuth credentials are set up.
    """
    if not settings.dev_login_allowed:
        raise HTTPException(404, "not found")

    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "a valid email is required")

    request.session[SESSION_USER_KEY] = {
        "id": f"dev:{email}",
        "email": email,
        "name": body.name or email.split("@")[0],
        "picture": "",
    }
    await _remember(request.session[SESSION_USER_KEY], None)
    return request.session[SESSION_USER_KEY]


@router.get("/config")
async def auth_config():
    """Lets the sign-in page show only the options that actually work here."""
    return {
        "google": bool(settings.google_client_id),
        "dev_login": settings.dev_login_allowed,
    }


class AndroidSessionIn(BaseModel):
    id_token: str
    nonce: str
    device: str = "Android"


class AndroidSessionOut(BaseModel):
    token: str
    expires_at: datetime
    user: User


async def verify_android_token(body: AndroidSessionIn) -> dict:
    """Verify Google's signed ID token and the nonce supplied to Credential Manager."""
    if not settings.google_client_id:
        raise HTTPException(500, "GOOGLE_CLIENT_ID is not configured")

    try:
        claims = await asyncio.to_thread(
            verify_google_id_token, body.id_token, settings.google_client_id
        )
    except ValueError as exc:
        raise HTTPException(401, "Google ID token is invalid") from exc
    validate_android_claims(claims, body)
    return claims


def verify_google_id_token(encoded: str, audience: str, request=None) -> dict:
    """Google's real signature, issuer, audience, and expiry verifier.

    ``request`` is injectable only so the cryptographic contract can run with
    a local certificate response instead of depending on Google's network.
    Production always uses Google's transport.
    """
    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2 import id_token

    try:
        return id_token.verify_oauth2_token(encoded, request or GoogleRequest(), audience)
    except GoogleAuthError as exc:
        raise ValueError("Google ID token issuer is invalid") from exc


def validate_android_claims(claims: dict, body: AndroidSessionIn) -> None:
    if claims.get("nonce") != body.nonce:
        raise HTTPException(401, "Google ID token nonce does not match")
    if not claims.get("email") or claims.get("email_verified") is not True:
        raise HTTPException(401, "Google account email is not verified")


async def current_user(
    request: Request,
    ctx: Context = Depends(get_context),
) -> dict:
    """FastAPI dependency — 401s unauthenticated callers.

    A browser carries its signed-in session cookie. Android carries a revocable
    device token issued after native Google ID-token verification. Older APKs
    may still hold the same token shape from pairing. Everything downstream
    sees one Photographer dict and does not need to know which door was used.
    """
    user = request.session.get(SESSION_USER_KEY)
    if user:
        await _refuse_sample_write(request, ctx, user["id"])
        return user

    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() == "bearer" and token:
        from app.api import pairing

        device = await repo.find_device(ctx.store, pairing.token_fingerprint(token.strip()))
        if device:
            expires = device.get("expires_at")
            if expires and datetime.fromisoformat(expires) <= datetime.now(now().tzinfo):
                await repo.delete_device(ctx.store, device["fingerprint"])
                raise HTTPException(401, "device session expired")
            user = await repo.find_user(ctx.store, device["user_id"])
            await _refuse_sample_write(request, ctx, device["user_id"])
            return {
                "id": device["user_id"],
                "email": user.email if user else "",
                "name": user.name if user else "",
                "picture": user.picture if user else "",
                "device": device.get("label", "camera"),
                "device_id": device.get("fingerprint", ""),
            }

    raise HTTPException(401, "not signed in")


async def _refuse_sample_write(request: Request, ctx: Context, user_id: str) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    user = await repo.find_user(ctx.store, user_id)
    if user is not None and user.record_mode is RecordMode.SAMPLE:
        raise HTTPException(409, "Sample Records are read-only interface fixtures")
