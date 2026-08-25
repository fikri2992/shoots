"""Pairing the camera to an account, without a browser on the phone.

The web signs in with Google and holds a session cookie. A native camera has
neither, and putting an OAuth flow inside the app would mean shipping a client
secret to a device. So the phone never authenticates: it is *handed* an
identity by a browser that already has one.

The signed-in web page asks for a short code and shows it. The photographer
types it into the camera once. The camera exchanges it for a device token and
stores it; from then on it carries that token and the code is spent.

Three properties this has to have, all of them cheap:

* a code is single use and short-lived, so a shoulder-surfer has minutes and
  one attempt rather than an open door;
* the token is the only long-lived secret, it never crosses a URL, and it is
  stored hashed so the store is not a credential file;
* the device is named, so a photographer can see what is paired.
"""

import hashlib
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.auth import SESSION_USER_KEY
from app.api.deps import get_context
from app.domain.entities import now
from app.infra import repository as repo
from app.services.context import Context

router = APIRouter(prefix="/api/pair", tags=["pairing"])

#: Long enough to type, short enough to read off a screen out loud.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I, O, 0, 1
CODE_LENGTH = 6
CODE_TTL = timedelta(minutes=10)


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def token_fingerprint(token: str) -> str:
    """What is stored. A device token is a bearer credential, so the store
    keeps a hash of it and never the token itself."""
    return hashlib.sha256(token.encode()).hexdigest()


class CodeOut(BaseModel):
    code: str
    expires_in_seconds: int


@router.post("", response_model=CodeOut)
async def create_code(request: Request, ctx: Context = Depends(get_context)):
    """The signed-in web page asks for a code to show the photographer."""
    session_user = request.session.get(SESSION_USER_KEY)
    if not session_user:
        raise HTTPException(401, "not signed in")
    code = new_code()
    await repo.put_pairing_code(ctx.store, code, session_user["id"], now() + CODE_TTL)
    return CodeOut(code=code, expires_in_seconds=int(CODE_TTL.total_seconds()))


class ClaimIn(BaseModel):
    code: str
    device: str = Field(default="camera", max_length=60)


class ClaimOut(BaseModel):
    token: str
    user_id: str


@router.post("/claim", response_model=ClaimOut)
async def claim(body: ClaimIn, ctx: Context = Depends(get_context)):
    """The camera exchanges the typed code for its own long-lived token.

    Unauthenticated by necessity — this is the call that creates the phone's
    identity. The code is the whole secret, which is why it dies on first use
    and after ten minutes either way.
    """
    user_id = await repo.spend_pairing_code(ctx.store, body.code.strip().upper(), now())
    if user_id is None:
        raise HTTPException(404, "that code is not valid any more")
    token = secrets.token_urlsafe(32)
    await repo.put_device(ctx.store, token_fingerprint(token), user_id, body.device)
    await repo.record(ctx.store, user_id, "pairing", "paired", {"device": body.device})
    return ClaimOut(token=token, user_id=user_id)
