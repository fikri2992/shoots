"""What the user hears about, and how: one push per event that matters.

Subscriptions live in the ``push`` collection keyed by a hash of the
endpoint, one per device. Dead ones are removed on the first 404/410.
Delivery problems are logged and never fail the stage that triggered them.
"""

import hashlib
import logging

from app.config import settings
from app.domain.entities import Experiment, Verdict
from app.infra import push
from app.infra.store import Store
from app.services.context import Context

logger = logging.getLogger(__name__)

PUSH = "push"


def subscription_id(user_id: str, endpoint: str) -> str:
    return f"{user_id}__{hashlib.sha1(endpoint.encode()).hexdigest()[:16]}"


async def subscribe(store: Store, user_id: str, subscription: dict) -> str:
    endpoint = subscription.get("endpoint", "")
    if not endpoint or "keys" not in subscription:
        raise ValueError("a push subscription needs an endpoint and keys")
    sid = subscription_id(user_id, endpoint)
    await store.put(PUSH, sid, {"id": sid, "user_id": user_id, "subscription": subscription})
    return sid


async def unsubscribe(store: Store, user_id: str, endpoint: str) -> None:
    await store.delete(PUSH, subscription_id(user_id, endpoint))


async def list_subscriptions(store: Store, user_id: str) -> list[dict]:
    return await store.query(PUSH, where={"user_id": user_id})


async def notify(
    ctx: Context, user_id: str, title: str, body: str, url: str = "/", tag: str = ""
) -> int:
    """Send to every device. Returns how many deliveries succeeded."""
    if not settings.vapid_private_key:
        return 0
    delivered = 0
    for row in await list_subscriptions(ctx.store, user_id):
        try:
            alive = await push.send(
                row["subscription"], {"title": title, "body": body[:180], "url": url, "tag": tag}
            )
        except Exception as error:  # noqa: BLE001 — logged, never fatal
            logger.warning("push to %s failed: %s", user_id, str(error)[:200])
            continue
        if alive:
            delivered += 1
        else:
            await ctx.store.delete(PUSH, row["id"])
    return delivered


# --- the events that matter ------------------------------------------------


async def quest_issued(ctx: Context, experiment: Experiment) -> None:
    await notify(
        ctx,
        experiment.user_id,
        f"Today's experiment: {experiment.title}",
        experiment.why_now or experiment.brief.split("\n", 1)[0],
        url="/",
        tag=f"experiment-{experiment.id}",
    )


async def verdict_given(ctx: Context, experiment: Experiment, verdict: Verdict) -> None:
    first_line = verdict.feedback.split("\n", 1)[0]
    await notify(
        ctx,
        experiment.user_id,
        f"{'Passed' if verdict.passed else 'Not yet'}: {experiment.title}",
        first_line,
        url=f"/shots/{verdict.shot_id}",
        tag=f"verdict-{verdict.shot_id}",
    )
