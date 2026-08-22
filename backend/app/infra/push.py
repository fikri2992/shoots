"""Web Push delivery (decision 12). One function, one outcome per subscription."""

import asyncio
import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

#: Push services answer these when a subscription is dead; delete it.
GONE = {404, 410}


class PushNotConfigured(RuntimeError):
    pass


async def send(subscription: dict[str, Any], payload: dict[str, Any], ttl: int = 3600) -> bool:
    """Deliver ``payload`` (title, body, url, tag) to one subscription.

    Returns False when the subscription is gone and should be removed. Any
    other failure raises, so the caller can log it with the user id.
    """
    if not settings.vapid_private_key:
        raise PushNotConfigured("VAPID_PRIVATE_KEY is not set")

    def run() -> bool:
        from pywebpush import WebPushException, webpush

        try:
            webpush(
                subscription_info=subscription,
                data=json.dumps(payload),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
                ttl=ttl,
            )
            return True
        except WebPushException as error:
            status = getattr(error.response, "status_code", None)
            if status in GONE:
                return False
            raise

    return await asyncio.to_thread(run)
