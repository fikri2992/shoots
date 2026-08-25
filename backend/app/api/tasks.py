"""Scheduled work. Cloud Scheduler calls these daily; locally, curl does.

Auth: a shared token header now; on Cloud Run an OIDC-authenticated
Scheduler job with the same header (day 7 swaps the check for token
verification). Everything here is idempotent, so a retry is harmless.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.api.deps import get_context
from app.config import settings
from app.infra import repository as repo
from app.services import ingest, scout, watch
from app.services.context import Context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


class DailyReport(BaseModel):
    users: int
    synced: int
    expired: int
    issued: int
    delivered: int = 0
    errors: list[str]


def _authorised(token: str | None) -> None:
    if not settings.tasks_token or token != settings.tasks_token:
        raise HTTPException(401, "bad tasks token")


@router.post("/daily", response_model=DailyReport)
async def daily(
    x_tasks_token: str | None = Header(default=None), ctx: Context = Depends(get_context)
):
    """The tick: sync every folder, expire what has run out, offer something to
    anyone with nothing open. Per user, errors are recorded, not fatal.

    Nothing decays here any more. The Technique Map records what the Evidence
    observed and does not un-observe it with time (decision 46); whether age
    makes something worth revisiting is a selection question the Scout answers
    at the moment it chooses.
    """
    _authorised(x_tasks_token)
    report = DailyReport(users=0, synced=0, expired=0, issued=0, errors=[])
    for user in await repo.list_users(ctx.store):
        report.users += 1
        try:
            report.synced += len(await ingest.sync(ctx, user))
            report.expired += len(await scout.expire(ctx, user.id))
            if await scout.issue(ctx, user.id):
                report.issued += 1
            await watch.ensure(ctx, user)
        except Exception as error:  # one user's failure must not stop the tick
            logger.exception("daily tick failed for %s", user.id)
            report.errors.append(f"{user.id}: {type(error).__name__}: {error}"[:200])
    report.delivered = await scout.deliver_due(ctx)
    await repo.record(
        ctx.store, "system", "scheduler", "daily", report.model_dump()
    ) if report.users else None
    return report


@router.post("/renew-channels")
async def renew_channels(
    x_tasks_token: str | None = Header(default=None), ctx: Context = Depends(get_context)
):
    """Re-open Drive push channels near expiry. Scheduled twice a day; Drive
    caps a channel at one day."""
    _authorised(x_tasks_token)
    return {"renewed": await watch.renew_all(ctx)}


@router.post("/tick")
async def tick(
    x_tasks_token: str | None = Header(default=None), ctx: Context = Depends(get_context)
):
    """Every few minutes: sync every folder (the belt to the Drive channel's
    braces) and push any quest whose light window has opened."""
    _authorised(x_tasks_token)
    queued = 0
    for user in await repo.list_users(ctx.store):
        queued += len(await ingest.sync(ctx, user))
    delivered = await scout.deliver_due(ctx)
    return {"queued": queued, "delivered": delivered}
