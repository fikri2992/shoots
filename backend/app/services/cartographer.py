"""Cartographer stage: ``media.analyzed`` → Technique Map, then the Journey.

The map itself is pure. The Journey Update that follows is arithmetic too —
``services/journey.py`` decides whether anything moved — and calls one writer
only when it did, so an update never arrives with nothing behind it.
"""

import logging

from app.domain import technique_map as rules
from app.domain.entities import TechniqueStatus, now
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

    states = {
        state.technique_id: state
        for state in await repo.list_technique_states(ctx.store, shot.user_id)
    }
    before = {technique_id: state.status for technique_id, state in states.items()}
    changed = rules.apply_analysis(states, analysis, at=shot.captured_at or now())
    if not changed:
        await repo.record(
            ctx.store,
            shot.user_id,
            AGENT,
            "map_unchanged",
            {"reason": "this Shot added no new Technique state"},
            shot_id=shot.id,
        )
        await _journey(ctx, shot.user_id)
        return

    for state in changed:
        await repo.put_technique_state(ctx.store, state)

    await repo.record(
        ctx.store,
        shot.user_id,
        AGENT,
        "mapped",
        {
            "changes": [
                {
                    "technique_id": s.technique_id,
                    # The feed renders this word. `unexplored` was retired with
                    # the other four graded states (decision 46); a Technique
                    # the record has not seen is `unobserved`.
                    "from": before.get(s.technique_id, TechniqueStatus.UNOBSERVED).value,
                    "to": s.status.value,
                    "attempts": s.attempts,
                    "corroborated": s.corroborated,
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
    Technique Map is already stored.
    """
    try:
        await scout.check_advice(ctx, user_id)
    except Exception:  # noqa: BLE001 — the map stands without the grade
        logger.exception("checking the Scout's advice failed for %s", user_id)
    try:
        await journey.maybe_write(ctx, user_id)
    except Exception:  # noqa: BLE001 — the map stands without the prose
        logger.exception("journey update failed for %s", user_id)
