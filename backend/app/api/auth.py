"""Google OAuth — the only sign-in path (domain-model.md decision 8)."""

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": settings.oauth_scopes, "access_type": "offline", "prompt": "consent"},
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

    request.session[SESSION_USER_KEY] = {
        "id": claims["sub"],
        "email": claims["email"],
        "name": claims.get("name", ""),
        "picture": claims.get("picture", ""),
    }
    return RedirectResponse(settings.frontend_origin)


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
    return request.session[SESSION_USER_KEY]


@router.get("/config")
async def auth_config():
    """Lets the sign-in page show only the options that actually work here."""
    return {
        "google": bool(settings.google_client_id),
        "dev_login": settings.dev_login_allowed,
    }


def current_user(request: Request) -> dict:
    """FastAPI dependency — 401s unauthenticated callers."""
    user = request.session.get(SESSION_USER_KEY)
    if not user:
        raise HTTPException(401, "not signed in")
    return user
