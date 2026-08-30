"""What the user hears about, and how: one push per event that matters.

Subscriptions live in the ``push`` collection keyed by a hash of the
endpoint, one per device. Dead ones are removed on the first 404/410.
Delivery problems are logged and never fail the stage that triggered them.
"""

import hashlib
import logging

from app.config import settings
from app.domain.entities import CaptureSession, Experiment, Verdict
from app.infra import push
from app.infra import repository as repo
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


async def notify_mobile(
    ctx: Context,
    user_id: str,
    title: str,
    body: str,
    *,
    route: str,
    tag: str,
    kind: str,
) -> int:
    """Deliver sparse native notifications without making pipeline work fail."""
    if ctx.mobile_push is None:
        return 0
    delivered = 0
    for device in await repo.list_devices(ctx.store, user_id):
        target = str(device.get("notification_target", ""))
        if not target:
            continue
        try:
            alive = await ctx.mobile_push.send(
                target,
                {
                    "kind": kind,
                    "title": title[:100],
                    "body": body[:180],
                    "route": route,
                    "tag": tag,
                },
                tag=tag,
            )
        except Exception as error:  # noqa: BLE001 - notification failure is not stage failure
            logger.warning("mobile push to %s failed: %s", user_id, str(error)[:200])
            continue
        if alive:
            delivered += 1
        else:
            await repo.set_device_notification_target(ctx.store, device["fingerprint"], "")
    return delivered


# --- the events that matter ------------------------------------------------


async def experiment_issued(ctx: Context, experiment: Experiment) -> None:
    title = f"A Shot idea for today: {experiment.title}"
    body = experiment.why_now or experiment.brief.split("\n", 1)[0]
    tag = f"experiment-{experiment.id}"
    await notify(
        ctx,
        experiment.user_id,
        title,
        body,
        url="/",
        tag=tag,
    )
    await notify_mobile(
        ctx,
        experiment.user_id,
        title,
        body,
        route="now",
        tag=tag,
        kind="experiment",
    )


async def verdict_given(ctx: Context, experiment: Experiment, verdict: Verdict) -> None:
    """A Verdict answers the Criteria, so the push says so. "Passed" would put a
    grade on the photographer's lock screen for something that was only ever a
    list of checks they declared in advance (decision 46)."""
    first_line = verdict.feedback.split("\n", 1)[0]
    await notify(
        ctx,
        experiment.user_id,
        f"{'Matched every check' if verdict.criteria_met else 'Not yet'}: {experiment.title}",
        first_line,
        url=f"/shots/{verdict.shot_id}",
        tag=f"verdict-{verdict.shot_id}",
    )


async def capture_session_settled(ctx: Context, session: CaptureSession) -> int:
    total = session.summary.get("members", len(session.members))
    met = session.summary.get("criteria_met", 0)
    terminal = session.summary.get("terminal", 0)
    body = f"Shoots finished reading {total} {'Shot' if total == 1 else 'Shots'}"
    if met:
        body += f" · {met} matched every check"
    if terminal:
        body += f" · {terminal} could not be read"
    return await notify_mobile(
        ctx,
        session.user_id,
        "Your results are ready",
        body,
        route="journey",
        tag=f"capture-session-{session.id}",
        kind="capture_session",
    )
