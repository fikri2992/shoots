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
from app.domain import skills as skill_rules
from app.domain.entities import now
from app.infra import repository as repo
from app.services import ingest, scout
from app.services.context import Context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


class DailyReport(BaseModel):
    users: int
    synced: int
    expired: int
    decayed: int
    issued: int
    errors: list[str]


def _authorised(token: str | None) -> None:
    if not settings.tasks_token or token != settings.tasks_token:
        raise HTTPException(401, "bad tasks token")


@router.post("/daily", response_model=DailyReport)
async def daily(
    x_tasks_token: str | None = Header(default=None), ctx: Context = Depends(get_context)
):
    """The tick: sync every folder, expire stale quests, decay skills, issue
    a quest to anyone without one. Per user, errors are recorded, not fatal."""
    _authorised(x_tasks_token)
    report = DailyReport(users=0, synced=0, expired=0, decayed=0, issued=0, errors=[])
    for user in await repo.list_users(ctx.store):
        report.users += 1
        try:
            report.synced += len(await ingest.sync(ctx, user))
            report.expired += len(await scout.expire(ctx, user.id))
            skills = {s.technique_id: s for s in await repo.list_skills(ctx.store, user.id)}
            for state in skill_rules.decay(skills, now(), settings.skill_decay_days):
                await repo.put_skill(ctx.store, state)
                report.decayed += 1
            if await scout.issue(ctx, user.id):
                report.issued += 1
        except Exception as error:  # one user's failure must not stop the tick
            logger.exception("daily tick failed for %s", user.id)
            report.errors.append(f"{user.id}: {type(error).__name__}: {error}"[:200])
    await repo.record(
        ctx.store, "system", "scheduler", "daily", report.model_dump()
    ) if report.users else None
    return report


@router.post("/sync")
async def sync_all(
    x_tasks_token: str | None = Header(default=None), ctx: Context = Depends(get_context)
):
    """Folder sync only. Runs every few minutes as a belt to the Drive
    push channel's braces."""
    _authorised(x_tasks_token)
    queued = 0
    for user in await repo.list_users(ctx.store):
        queued += len(await ingest.sync(ctx, user))
    return {"queued": queued}
