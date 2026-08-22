"""Cartographer stage: ``media.analyzed`` → skill graph. No model."""

import logging

from app.domain import skills as rules
from app.domain.entities import now
from app.infra import repository as repo
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "cartographer"


async def update(ctx: Context, message: dict) -> None:
    shot = await repo.get_shot(ctx.store, message["shot_id"])
    analysis = await repo.find_analysis(ctx.store, shot.id)
    if analysis is None:
        logger.warning("cartographer: no analysis for %s", shot.id)
        return

    skills = {s.technique_id: s for s in await repo.list_skills(ctx.store, shot.user_id)}
    before = {tid: s.status for tid, s in skills.items()}
    changed = rules.apply_analysis(skills, analysis, at=shot.captured_at or now())
    if not changed:
        return

    for state in changed:
        await repo.put_skill(ctx.store, state)

    await repo.record(
        ctx.store,
        shot.user_id,
        AGENT,
        "mapped",
        {
            "changes": [
                {
                    "technique_id": s.technique_id,
                    "from": before.get(s.technique_id, "unexplored"),
                    "to": s.status.value,
                    "attempts": s.attempts,
                    "best": s.best_score,
                }
                for s in changed
            ]
        },
        shot_id=shot.id,
    )
