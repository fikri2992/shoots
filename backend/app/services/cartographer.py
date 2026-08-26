"""Cartographer stage: ``media.analyzed`` → Technique Map, then the Journey.

The map itself is pure. The Journey Update that follows is arithmetic too —
``services/journey.py`` decides whether anything moved — and calls one writer
only when it did, so an update never arrives with nothing behind it.
"""

import logging

from app.domain import technique_projection
from app.domain.entities import CaptureMemberOutcome, TechniqueState
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

    before = {
        state.technique_id: state
        for state in await repo.list_technique_states(ctx.store, shot.user_id)
    }
    states = await rebuild(ctx, shot.user_id)
    changed = [
        state
        for technique_id, state in states.items()
        if technique_id not in before or state != before[technique_id]
    ]
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
                    "from": before.get(
                        s.technique_id,
                        TechniqueState(user_id=s.user_id, technique_id=s.technique_id),
                    ).status.value,
                    "to": s.status.value,
                    "sightings": s.sightings,
                    "corroborated_shots": s.corroborated_shots,
                    "distinct_scenes": s.distinct_scenes,
                    "distinct_shoots": s.distinct_shoots,
                }
                for s in changed
            ]
        },
        shot_id=shot.id,
    )
    await _journey(ctx, shot.user_id)


async def rebuild(ctx: Context, user_id: str) -> dict[str, TechniqueState]:
    """Rebuild current Technique evidence from authoritative Photographer records."""
    shots = await repo.list_shots(ctx.store, user_id)
    scenes_by_shot: dict[str, str] = {}
    shoots_by_shot: dict[str, str] = {}
    for shoot in await repo.list_shoots(ctx.store, user_id):
        for scene in await repo.list_scenes_for_shoot(ctx.store, shoot.id):
            if scene.grouping_revision != shoot.revision:
                continue
            for shot_id in scene.ordered_shot_ids:
                scenes_by_shot[shot_id] = scene.id
                shoots_by_shot[shot_id] = shoot.id
    experiments = await repo.list_experiments(ctx.store, user_id)
    capture_sessions = await repo.list_capture_sessions(ctx.store, user_id, limit=None)
    abstained: dict[str, set[str]] = {}
    for session in capture_sessions:
        for member in session.members:
            if member.shot_id and member.outcome is CaptureMemberOutcome.ABSTAINED:
                abstained.setdefault(session.experiment_id, set()).add(member.shot_id)
    previous = await repo.list_technique_states(ctx.store, user_id)
    projection = technique_projection.build(
        technique_projection.ProjectionInputs(
            user_id=user_id,
            analyses=tuple(await repo.list_analyses(ctx.store, user_id)),
            shots={
                shot.id: technique_projection.ShotFact(
                    observed_at=shot.captured_at or shot.ingested_at,
                    kept=shot.kept_at is not None,
                    scene_id=scenes_by_shot.get(shot.id, ""),
                    shoot_id=shoots_by_shot.get(shot.id, ""),
                )
                for shot in shots
            },
            experiments=tuple(experiments),
            capture_sessions=tuple(capture_sessions),
            abstained_by_experiment={
                experiment_id: frozenset(shot_ids) for experiment_id, shot_ids in abstained.items()
            },
            existing_technique_ids=frozenset(state.technique_id for state in previous),
        )
    )
    for state in projection.values():
        await repo.put_technique_state(ctx.store, state)
    return projection


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
