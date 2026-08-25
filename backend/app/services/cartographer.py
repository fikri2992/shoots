"""Cartographer stage: ``media.analyzed`` → skill graph, then the Journey.

The map itself is pure. The Journey Update that follows is arithmetic too —
``services/journey.py`` decides whether anything moved — and calls one writer
only when it did, so an update never arrives with nothing behind it.
"""

import logging

from app.domain import technique_map as rules
from app.domain.entities import now
from app.infra import repository as repo
from app.services import journey, scout
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
        await _journey(ctx, shot.user_id)
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
    await _journey(ctx, shot.user_id)


async def _journey(ctx: Context, user_id: str) -> None:
    """Two questions after every reading, both arithmetic.

    Did the Scout's own advice change anything (decision 37), and has the body
    of work moved enough to be worth a paragraph? Usually the second is no and
    nothing is written. A failure in either costs the prose, not the map: the
    skill graph is already stored.
    """
    try:
        await scout.grade_advice(ctx, user_id)
    except Exception:  # noqa: BLE001 — the map stands without the grade
        logger.exception("grading the Scout's advice failed for %s", user_id)
    try:
        await journey.maybe_write(ctx, user_id)
    except Exception:  # noqa: BLE001 — the map stands without the prose
        logger.exception("journey update failed for %s", user_id)
