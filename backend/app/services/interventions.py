"""Project immutable Scout decisions into observable intervention outcomes."""

from collections import Counter

from app.domain.entities import (
    CaptureMemberOutcome,
    ChangeState,
    ExperimentStatus,
    InterventionAttemptState,
    InterventionOutcome,
    InterventionRecord,
    ScoutAnswer,
    ScoutDecision,
    Shoot,
    now,
)
from app.infra import repository as repo
from app.services.context import Context


async def record_decision(
    ctx: Context,
    shoot: Shoot,
    decision: ScoutDecision,
) -> InterventionRecord:
    warrant_shot_ids = list(
        dict.fromkeys(shot_id for warrant in decision.warrant for shot_id in warrant.shot_ids)
    )
    technique_id = next(
        (warrant.technique_id for warrant in decision.warrant if warrant.technique_id),
        "",
    )
    intervention = InterventionRecord(
        id=intervention_id(shoot.id, shoot.revision),
        user_id=shoot.user_id,
        shoot_id=shoot.id,
        shoot_revision=shoot.revision,
        route=decision.route,
        technique_id=technique_id,
        question_id=decision.question.id,
        recommendation_id=decision.recommendation.id,
        recommendation_option_id=decision.recommendation.primary_option_id,
        experiment_id=decision.experiment_id,
        warrant_shot_ids=warrant_shot_ids,
        attempt_state=decision.attempt_state,
        delivered_at=decision.executed_at,
        outcome_reason=decision.execution_detail,
        updated_at=decision.executed_at or decision.decided_at,
    )
    return await repo.put_intervention_once(ctx.store, intervention)


async def link_answer(ctx: Context, answer: ScoutAnswer) -> InterventionRecord | None:
    intervention = await repo.find_intervention(
        ctx.store,
        intervention_id(answer.shoot_id, answer.shoot_revision),
    )
    if intervention is None:
        return None
    intervention.experiment_id = answer.experiment_id
    intervention.technique_id = answer.technique_id or intervention.technique_id
    intervention.attempt_state = InterventionAttemptState.COMPLETED
    intervention.outcome_reason = answer.detail
    intervention.updated_at = answer.answered_at
    await repo.put_intervention(ctx.store, intervention)
    return intervention


async def mark_entered(ctx: Context, user_id: str, experiment_id: str) -> InterventionRecord | None:
    intervention = await repo.find_intervention_for_experiment(ctx.store, user_id, experiment_id)
    if intervention is None:
        return None
    if intervention.attempt_state in {
        InterventionAttemptState.OFFERED,
        InterventionAttemptState.ACCEPTED,
    }:
        intervention.attempt_state = InterventionAttemptState.ENTERED
        intervention.outcome_reason = "You opened the Experiment and started a Camera session."
        intervention.updated_at = now()
        await repo.put_intervention(ctx.store, intervention)
    return intervention


async def refresh_for_experiment(
    ctx: Context,
    experiment_id: str,
) -> InterventionRecord | None:
    experiment = await repo.get_experiment(ctx.store, experiment_id)
    intervention = await repo.find_intervention_for_experiment(
        ctx.store, experiment.user_id, experiment.id
    )
    if intervention is None:
        return None
    sessions = [
        session
        for session in await repo.list_capture_sessions(ctx.store, experiment.user_id, limit=None)
        if session.experiment_id == experiment.id
    ]
    intervention.result_shot_ids = list(experiment.result_shot_ids)
    intervention.criteria_met_results = sum(verdict.criteria_met for verdict in experiment.verdicts)
    intervention.abstentions = sum(
        member.outcome is CaptureMemberOutcome.ABSTAINED
        for session in sessions
        for member in session.members
    )
    intervention.variation_ids = list(
        dict.fromkeys(session.variation_id for session in sessions if session.variation_id)
    )
    if experiment.status is ExperimentStatus.OPEN:
        intervention.attempt_state = (
            InterventionAttemptState.ENTERED
            if sessions
            else (
                InterventionAttemptState.ACCEPTED
                if intervention.attempt_state is InterventionAttemptState.ACCEPTED
                else InterventionAttemptState.OFFERED
            )
        )
        intervention.outcome_reason = (
            "You started trying this Experiment with the Camera."
            if sessions
            else (
                "You accepted the Experiment. No Camera session has started yet."
                if intervention.attempt_state is InterventionAttemptState.ACCEPTED
                else "The Experiment is still waiting if you want it."
            )
        )
    elif experiment.status in {ExperimentStatus.LEFT, ExperimentStatus.SKIPPED}:
        intervention.attempt_state = InterventionAttemptState.LEFT
        intervention.outcome_reason = "You left the Experiment. Shoots did not guess why."
    elif experiment.status is ExperimentStatus.EXPIRED:
        intervention.attempt_state = InterventionAttemptState.LEFT
        intervention.outcome_reason = (
            "The Experiment ran out of time. Shoots did not treat that as a result."
        )
    else:
        intervention.attempt_state = InterventionAttemptState.COMPLETED
        if experiment.change is not None:
            intervention.observable_outcome = {
                ChangeState.CHANGED: InterventionOutcome.CHANGED,
                ChangeState.UNCHANGED: InterventionOutcome.UNCHANGED,
                ChangeState.INSUFFICIENT: InterventionOutcome.INSUFFICIENT_EVIDENCE,
            }[experiment.change.state]
            intervention.change_state = experiment.change.state.value
            intervention.comparability = experiment.change.comparability.value
            intervention.outcome_reason = experiment.change.outcome
        else:
            intervention.observable_outcome = InterventionOutcome.NOT_APPLICABLE
            intervention.outcome_reason = (
                "You finished the Experiment, but there are no similar later Shots to compare yet."
            )
    intervention.updated_at = now()
    await repo.put_intervention(ctx.store, intervention)
    return intervention


async def deprioritized_technique_ids(ctx: Context, user_id: str) -> set[str]:
    counts = Counter(
        intervention.technique_id
        for intervention in await repo.list_interventions(ctx.store, user_id, limit=None)
        if intervention.technique_id
        and intervention.attempt_state is InterventionAttemptState.COMPLETED
        and intervention.observable_outcome is InterventionOutcome.UNCHANGED
        and intervention.comparability in {"", "comparable"}
    )
    return {technique_id for technique_id, count in counts.items() if count >= 2}


def intervention_id(shoot_id: str, revision: int) -> str:
    return f"intervention_{shoot_id}_r{revision}"
