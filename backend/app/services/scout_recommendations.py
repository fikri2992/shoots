"""Accept or leave one stored Scout Recommendation without inventing Intent."""

from app.domain import taxonomy
from app.domain.entities import (
    Experiment,
    ExperimentType,
    InterventionAttemptState,
    InterventionRecord,
    PhotographerSignal,
    PhotographerSignalKind,
    ScoutDecision,
    ScoutRecommendationAction,
    ScoutRecommendationOption,
    ScoutRoute,
    SignalScope,
    SignalSource,
    now,
)
from app.infra import repository as repo
from app.services import interventions, photographer_memory
from app.services import scout as experiment_scout
from app.services.context import Context


class RecommendationConflict(ValueError):
    pass


async def respond(
    ctx: Context,
    user_id: str,
    shoot_id: str,
    revision: int,
    action: ScoutRecommendationAction,
    option_id: str = "",
) -> tuple[InterventionRecord, Experiment | None]:
    record = await repo.find_shoot_record(ctx.store, shoot_id, revision)
    if record is None or record.user_id != user_id:
        raise repo.UnknownEntity(f"Shoot Record {shoot_id} revision {revision}")
    options = _options(record.scout)
    if not options:
        raise RecommendationConflict("This Shoot Record has no Scout Recommendation")
    intervention = await repo.find_intervention(
        ctx.store,
        interventions.intervention_id(shoot_id, revision),
    )
    if intervention is None:
        raise RecommendationConflict("The Scout Recommendation has no audit record")

    if action is ScoutRecommendationAction.ACCEPT:
        return await _accept(ctx, user_id, record.scout, intervention, options, option_id)
    if intervention.experiment_id:
        raise RecommendationConflict("This Recommendation already became an Experiment")
    if action is ScoutRecommendationAction.JUST_SHOOTING:
        await _record_just_shooting(ctx, user_id, shoot_id, record.scout)
        reason = "You said you were just shooting. Shoots left the meaning open."
        stage = "recommendation_calibrated"
    else:
        reason = "You left this recommendation for today. Shoots did not guess why."
        stage = "recommendation_left"
    intervention.attempt_state = InterventionAttemptState.LEFT
    intervention.outcome_reason = reason
    intervention.updated_at = now()
    await repo.put_intervention(ctx.store, intervention)
    await repo.record(
        ctx.store,
        user_id,
        "photographer",
        stage,
        {
            "recommendation_id": _recommendation_id(record.scout),
            "action": action.value,
        },
    )
    return intervention, None


async def _accept(
    ctx: Context,
    user_id: str,
    decision: ScoutDecision,
    intervention: InterventionRecord,
    options: list[ScoutRecommendationOption],
    option_id: str,
) -> tuple[InterventionRecord, Experiment]:
    selected_id = option_id or decision.recommendation.primary_option_id or options[0].id
    option = next((item for item in options if item.id == selected_id), None)
    if option is None:
        raise RecommendationConflict("That idea is not part of this Scout Recommendation")
    if intervention.experiment_id:
        experiment = await repo.find_experiment(ctx.store, intervention.experiment_id)
        if experiment is None or experiment.user_id != user_id:
            raise RecommendationConflict("The accepted Experiment is no longer available")
        if (
            intervention.recommendation_option_id
            and intervention.recommendation_option_id != option.id
        ):
            raise RecommendationConflict("A different idea from this Recommendation was accepted")
        return intervention, experiment
    if intervention.attempt_state is InterventionAttemptState.LEFT:
        raise RecommendationConflict("This Scout Recommendation was already left")

    experiment_id = f"experiment_{intervention.shoot_id}_r{intervention.shoot_revision}"
    recovered = await repo.find_experiment(ctx.store, experiment_id)
    if recovered is not None:
        experiment = recovered
    elif option.experiment_type is ExperimentType.REPRODUCE:
        experiment = await experiment_scout.issue(
            ctx,
            user_id,
            technique_id=option.technique_id,
            requested_reason="accepted_shoot_recommendation",
            experiment_id=experiment_id,
        )
    else:
        experiment = await experiment_scout.issue_explore(
            ctx,
            user_id,
            technique_id=option.technique_id,
            requested_reason=option.why_now,
            experiment_id=experiment_id,
            warrant_shot_ids=list(option.warrant_shot_ids),
            selection_basis="accepted_shoot_recommendation",
        )
    if experiment is None:
        raise RecommendationConflict("Another Experiment is already open")
    if experiment.user_id != user_id or experiment.technique_id != option.technique_id:
        raise RecommendationConflict("The Experiment does not match the accepted recommendation")

    intervention.recommendation_id = _recommendation_id(decision)
    intervention.recommendation_option_id = option.id
    intervention.technique_id = option.technique_id
    intervention.experiment_id = experiment.id
    intervention.attempt_state = InterventionAttemptState.ACCEPTED
    intervention.outcome_reason = (
        f"You accepted the {option.technique_name} Experiment. No Camera session has started yet."
    )
    intervention.updated_at = now()
    await repo.put_intervention(ctx.store, intervention)
    await repo.record(
        ctx.store,
        user_id,
        "photographer",
        "recommendation_accepted",
        {
            "recommendation_id": intervention.recommendation_id,
            "option_id": option.id,
            "technique_id": option.technique_id,
            "experiment_type": option.experiment_type.value,
        },
        experiment_id=experiment.id,
    )
    return intervention, experiment


def _options(decision: ScoutDecision) -> list[ScoutRecommendationOption]:
    if decision.route is ScoutRoute.RECOMMEND:
        return list(decision.recommendation.options)
    if decision.route is not ScoutRoute.ASK:
        return []
    options = []
    for legacy in decision.question.options:
        if not legacy.technique_id:
            continue
        technique = taxonomy.BY_ID.get(legacy.technique_id)
        if technique is None:
            continue
        warrant = next(
            (item for item in decision.warrant if item.technique_id == legacy.technique_id),
            None,
        )
        shot_ids = list(warrant.shot_ids) if warrant is not None else []
        count = len(set(shot_ids))
        why = (
            f"{count} Shot{'s' if count != 1 else ''} in this Shoot showed "
            f"{technique.name}. Try using that choice on purpose in a different Scene."
        )
        options.append(
            ScoutRecommendationOption(
                id=f"explore_{technique.id}",
                technique_id=technique.id,
                technique_name=technique.name,
                experiment_type=ExperimentType.EXPLORE,
                title=f"Try {technique.name} on purpose",
                why_now=why,
                warrant_shot_ids=shot_ids,
            )
        )
    return sorted(options, key=lambda item: (-len(set(item.warrant_shot_ids)), item.technique_id))


async def _record_just_shooting(
    ctx: Context,
    user_id: str,
    shoot_id: str,
    decision: ScoutDecision,
) -> None:
    value = "I was just shooting freely."
    recommendation_id = _recommendation_id(decision)
    signal_id = photographer_memory.stable_signal_id(
        user_id,
        SignalScope.SHOOT,
        shoot_id,
        PhotographerSignalKind.INTENT,
        value,
        f"scout_recommendation:{recommendation_id}",
    )
    await photographer_memory.apply_photographer_signal(
        ctx,
        PhotographerSignal(
            id=signal_id,
            user_id=user_id,
            scope=SignalScope.SHOOT,
            scope_id=shoot_id,
            kind=PhotographerSignalKind.INTENT,
            value=value,
            source=SignalSource.PHOTOGRAPHER_ACTION,
            source_event_id=f"evt_{recommendation_id}_calibrated",
        ),
    )


def _recommendation_id(decision: ScoutDecision) -> str:
    return decision.recommendation.id or decision.question.id
