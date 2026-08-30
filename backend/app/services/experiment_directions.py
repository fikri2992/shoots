"""Persist a later Technique question without pretending an Experiment started."""

from app.domain import taxonomy, technique_map
from app.domain.entities import (
    Experiment,
    ExperimentDirection,
    ExperimentDirectionState,
    now,
)
from app.infra import repository as repo
from app.services import scout
from app.services.context import Context


async def choose(
    ctx: Context,
    user_id: str,
    source_shot_id: str,
    technique_id: str,
    state: ExperimentDirectionState,
) -> ExperimentDirection:
    """Save or leave one Shot-grounded Direction idempotently."""
    if state is ExperimentDirectionState.STARTED:
        raise ValueError("Only starting the saved Direction may mark it started")
    technique = taxonomy.BY_ID.get(technique_id)
    if technique is None:
        raise ValueError("Unknown Technique")
    shot = await repo.find_shot(ctx.store, source_shot_id)
    if shot is None or shot.user_id != user_id or shot.superseded_by_inspiration_id:
        raise repo.UnknownEntity(f"Shot {source_shot_id}")
    analysis = await repo.find_analysis(ctx.store, shot.id)
    if analysis is None or not any(
        evidence.technique_id == technique_id and technique_map.corroborated(evidence)
        for evidence in analysis.techniques
    ):
        raise ValueError("That Shot has no corroborated Evidence for this Technique")

    direction_id = repo.experiment_direction_id_for(user_id, shot.id, technique_id)
    existing = await repo.find_experiment_direction(ctx.store, direction_id)
    if existing is not None and existing.state is ExperimentDirectionState.STARTED:
        return existing

    states = {
        item.technique_id: item
        for item in await repo.list_technique_states(ctx.store, user_id)
    }
    technique_state = states.get(technique_id)
    pattern = (await scout.keeper_patterns(ctx, user_id)).get(technique_id)
    if state is ExperimentDirectionState.SAVED and pattern is None:
        raise ValueError("Reproduce needs marked Keeper Evidence for this Technique")

    at = now()
    direction = ExperimentDirection(
        id=direction_id,
        user_id=user_id,
        source_shot_id=shot.id,
        technique_id=technique.id,
        technique_name=technique.name,
        question=f"Want to try {technique.name} again in a different Scene?",
        warrant_shot_ids=(
            list(pattern.shot_ids)
            if pattern is not None
            else list(existing.warrant_shot_ids if existing is not None else [])
        ),
        reference_shot_id=(
            pattern.reference_shot_id
            if pattern is not None
            else (existing.reference_shot_id if existing is not None else "")
        ),
        corroborated_shots=(
            technique_state.corroborated_shots if technique_state is not None else 0
        ),
        distinct_shoots=(technique_state.distinct_shoots if technique_state is not None else 0),
        state=state,
        created_at=existing.created_at if existing is not None else at,
        updated_at=at,
    )
    if existing is not None and direction.model_dump(exclude={"updated_at"}) == existing.model_dump(
        exclude={"updated_at"}
    ):
        return existing
    await repo.put_experiment_direction(ctx.store, direction)
    event_stage = (
        "experiment_direction_saved"
        if state is ExperimentDirectionState.SAVED
        else "experiment_direction_left"
    )
    await repo.record(
        ctx.store,
        user_id,
        "scout",
        event_stage,
        {
            "direction_id": direction.id,
            "technique_id": direction.technique_id,
            "warrant_shot_ids": direction.warrant_shot_ids,
        },
        shot_id=shot.id,
    )
    return direction


async def start(ctx: Context, user_id: str, direction_id: str) -> Experiment:
    """Turn one saved Direction into Reproduce, at most once."""
    direction = await repo.find_experiment_direction(ctx.store, direction_id)
    if direction is None or direction.user_id != user_id:
        raise repo.UnknownEntity(f"Experiment Direction {direction_id}")
    if direction.state is ExperimentDirectionState.STARTED:
        experiment = await repo.find_experiment(ctx.store, direction.started_experiment_id)
        if experiment is None or experiment.user_id != user_id:
            raise repo.UnknownEntity(f"Experiment {direction.started_experiment_id}")
        return experiment
    if direction.state is not ExperimentDirectionState.SAVED:
        raise ValueError("This Experiment Direction was left")
    if await repo.open_experiment(ctx.store, user_id) is not None:
        raise ValueError("Another Experiment is already open")
    if direction.technique_id not in await scout.keeper_patterns(ctx, user_id):
        raise ValueError("The saved Keeper warrant no longer supports Reproduce")

    experiment = await scout.issue(
        ctx,
        user_id,
        technique_id=direction.technique_id,
        requested_reason="saved_experiment_direction",
    )
    if experiment is None:
        if await repo.open_experiment(ctx.store, user_id) is not None:
            raise ValueError("Another Experiment became open")
        raise ValueError("Scout could not support this Experiment now")

    linked, _ = await repo.mark_experiment_direction_started(
        ctx.store,
        direction.id,
        experiment.id,
        now(),
    )
    if linked.state is not ExperimentDirectionState.STARTED:
        await scout.leave(ctx, user_id, experiment.id)
        raise ValueError("The saved Direction changed while it was starting")
    await repo.record(
        ctx.store,
        user_id,
        "scout",
        "experiment_direction_started",
        {
            "direction_id": direction.id,
            "technique_id": direction.technique_id,
            "reference_shot_id": experiment.reference_shot_id,
        },
        shot_id=direction.source_shot_id,
        experiment_id=experiment.id,
    )
    return experiment
