"""Pub/Sub push delivery: one endpoint per stage.

``infra/topics.sh`` creates a push subscription per stage pointing at
``/pubsub/<stage>``; Pub/Sub signs each request with an OIDC token for the
service account, which is verified here before anything runs. The handler
runs inline: a 2xx acks, anything else makes Pub/Sub retry and eventually
dead-letter, which is the whole resilience story (decision 7).
"""

import base64
import json
import logging

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from app.api.deps import get_context
from app.config import settings
from app.infra.bus import PubSubBus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pubsub", tags=["pubsub"])


class PushMessage(BaseModel):
    data: str = ""
    messageId: str = ""  # noqa: N815 — Pub/Sub's field names
    attributes: dict[str, str] = {}


class PushEnvelope(BaseModel):
    message: PushMessage
    subscription: str = ""


def decode(envelope: PushEnvelope) -> dict:
    """The message body is base64 JSON; stages only ever get small id dicts."""
    if not envelope.message.data:
        return {}
    raw = base64.b64decode(envelope.message.data)
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("pub/sub payload must be a JSON object")
    return payload


def verify(authorization: str | None) -> str:
    """Returns the verified caller email, or raises 401/403."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    try:
        claims = id_token.verify_oauth2_token(
            authorization.removeprefix("Bearer ").strip(),
            google_requests.Request(),
            audience=settings.pubsub_push_audience or None,
        )
    except Exception as error:  # noqa: BLE001 — any verification failure is a 401
        raise HTTPException(401, f"bad token: {str(error)[:120]}") from error
    email = claims.get("email", "")
    if not claims.get("email_verified") or email != settings.drive_service_account:
        raise HTTPException(403, f"unexpected caller {email!r}")
    return email


@router.post("/{stage}", status_code=204)
async def push(
    stage: str,
    envelope: PushEnvelope,
    request: Request,
    authorization: str | None = Header(default=None),
):
    verify(authorization)
    ctx = get_context()
    if not isinstance(ctx.bus, PubSubBus):
        raise HTTPException(409, "this instance runs the pipeline in-process")
    try:
        message = decode(envelope)
    except (ValueError, json.JSONDecodeError) as error:
        # Malformed: acking would lose it silently, nacking loops forever. Log
        # loudly and ack; the DLQ is for handler failures, not garbage.
        logger.error(
            "pub/sub %s: undecodable message %s: %s", stage, envelope.message.messageId, error
        )
        return None
    if stage not in ctx.bus.stages():
        raise HTTPException(404, f"unknown stage {stage!r}")
    await ctx.bus.deliver(stage, message)
    return None
