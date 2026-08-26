"""Typed Scout decision and action for one settled Shoot revision."""

from datetime import timedelta

from app.agents import scout as experiment_rules
from app.config import settings
from app.domain import scout as route_rules
from app.domain import taxonomy, tendency, timing
from app.domain.entities import (
    Experiment,
    ExperimentStatus,
    ExperimentTiming,
    ExperimentType,
    InterventionAttemptState,
    PhotographerSignalKind,
    ScoutDecision,
    ScoutExecutionState,
    ScoutQuestion,
    ScoutQuestionOption,
    ScoutRejectedRoute,
    ScoutRoute,
    ScoutWarrant,
    Shoot,
    ShootReceipt,
    SignalScope,
    User,
    now,
)
from app.infra import repository as repo
from app.services import interventions, photographer_memory
from app.services import scout as experiment_scout
from app.services.context import Context

POLICY_VERSION = "shoot-scout-3"


async def decide(
    ctx: Context,
    shoot: Shoot,
    receipt: ShootReceipt,
) -> ScoutDecision:
    """Choose and execute one code-gated action for a settled Shoot revision."""
    experiment_id = f"experiment_{shoot.id}_r{shoot.revision}"
    recovered = await repo.find_experiment(ctx.store, experiment_id)
    if recovered is not None:
        if recovered.user_id != shoot.user_id:
            raise repo.UnknownEntity(f"experiment {experiment_id}")
        if recovered.type is ExperimentType.EXPLORE:
            decision = _explore_decision(shoot, receipt, recovered)
        else:
            decision = _reproduce_decision(
                shoot,
                receipt,
                technique_id=recovered.technique_id,
                reference_shot_id=recovered.reference_shot_id,
                keeper_shot_ids=(
                    list(recovered.warrant_shot_ids)
                    if recovered.warrant_shot_ids
                    else [recovered.reference_shot_id]
                ),
                reason=recovered.why_now,
                experiment_id=recovered.id,
            )
        decision.execution_state = ScoutExecutionState.COMPLETED
        decision.execution_detail = "Existing deterministic Experiment recovered."
        decision.attempt_state = InterventionAttemptState.OFFERED
        decision.executed_at = now()
        await _record(ctx, shoot, decision)
        return decision

    open_experiment = await repo.open_experiment(ctx.store, shoot.user_id)
    patterns = await experiment_scout.keeper_patterns(ctx, shoot.user_id)
    recent = [
        experiment.technique_id
        for experiment in await repo.list_experiments(
            ctx.store,
            shoot.user_id,
            limit=experiment_scout.RECENT_EXPERIMENTS,
        )
    ]
    deprioritized = await interventions.deprioritized_technique_ids(ctx, shoot.user_id)
    user = await repo.get_user(ctx.store, shoot.user_id)
    constraints = await photographer_memory.constraints_for(
        ctx,
        shoot.user_id,
        scope=SignalScope.SHOOT,
        scope_id=shoot.id,
    )
    technique = route_rules.choose(
        tuple(patterns),
        [*recent, *sorted(deprioritized)],
        missing_gear=constraints.missing_gear,
    )
    reproduce_rejection = ""
    if open_experiment is not None:
        reproduce_rejection = f'Experiment "{open_experiment.id}" is already open.'
        technique = None
    elif not patterns:
        reproduce_rejection = "No marked Keeper has corroborated Technique Evidence yet."
    elif set(patterns) and set(patterns).issubset(deprioritized):
        reproduce_rejection = (
            "Automatic Reproduce was deprioritized after two comparable unchanged outcomes "
            "for the available Keeper-backed Technique."
        )
    elif technique is None:
        reproduce_rejection = (
            "Every Keeper-backed Technique was offered recently or conflicts with a constraint."
        )

    if technique is not None:
        pattern = patterns[technique.id]
        reason = (
            f"{pattern.count} marked Keeper{'s' if pattern.count != 1 else ''} include "
            f"{technique.name}; test whether you can make that decision deliberately."
        )
        decision = _reproduce_decision(
            shoot,
            receipt,
            technique_id=technique.id,
            reference_shot_id=pattern.reference_shot_id,
            keeper_shot_ids=list(pattern.shot_ids),
            reason=reason,
            experiment_id=experiment_id,
        )
        experiment = await _create_reproduce(
            ctx,
            user,
            technique,
            pattern,
            experiment_id,
            reason,
        )
        if experiment is not None:
            decision.execution_state = ScoutExecutionState.COMPLETED
            decision.execution_detail = "Reproduce Experiment offered."
            decision.attempt_state = InterventionAttemptState.OFFERED
            decision.executed_at = now()
            await _record(ctx, shoot, decision)
            await experiment_scout.deliver_if_due(ctx, experiment)
            return decision

        current = await repo.open_experiment(ctx.store, shoot.user_id)
        reproduce_rejection = (
            f'Experiment "{current.id}" won the open claim.'
            if current is not None
            else "The one-open Experiment claim changed before execution."
        )

    current_open = await repo.open_experiment(ctx.store, shoot.user_id)
    exact_intent = any(
        signal.scope is SignalScope.SHOOT
        and signal.scope_id == shoot.id
        and signal.kind is PhotographerSignalKind.INTENT
        for signal in await repo.list_photographer_signals(ctx.store, shoot.user_id)
    )
    question_techniques = _question_techniques(
        receipt,
        constraints.missing_gear,
        deprioritized,
    )
    ask_rejection = ""
    if current_open is not None:
        ask_rejection = f'Experiment "{current_open.id}" already owns the open slot.'
    elif exact_intent:
        ask_rejection = "This Shoot already has Photographer-owned Intent."
    elif len(question_techniques) < 2:
        ask_rejection = "Fewer than two corroborated Technique directions need clarification."
    else:
        decision = _ask_decision(shoot, receipt, question_techniques)
        decision.rejected_routes = _rejections(
            selected=ScoutRoute.ASK,
            reproduce_reason=reproduce_rejection,
        )
        decision.execution_state = ScoutExecutionState.COMPLETED
        decision.execution_detail = "One consequential Intent question is ready."
        decision.attempt_state = InterventionAttemptState.OFFERED
        decision.executed_at = now()
        await _record(ctx, shoot, decision)
        return decision

    explore_rejection = ""
    if current_open is not None:
        explore_rejection = f'Experiment "{current_open.id}" already owns the open slot.'
    else:
        explored = await experiment_scout.issue_explore(
            ctx,
            shoot.user_id,
            experiment_id=experiment_id,
            exclude_technique_ids=deprioritized,
        )
        if explored is not None:
            decision = _explore_decision(shoot, receipt, explored)
            decision.execution_state = ScoutExecutionState.COMPLETED
            decision.execution_detail = "Explore Variations offered."
            decision.attempt_state = InterventionAttemptState.OFFERED
            decision.executed_at = now()
            await _record(ctx, shoot, decision)
            return decision
        explore_rejection = "No supported Tendency Direction is available for Explore."

    if receipt.repeated or receipt.varied:
        decision = ScoutDecision(
            route=ScoutRoute.EXPLAIN,
            reason="This Shoot has a supported pattern worth showing without prescribing a task.",
            warrant=[_receipt_warrant(shoot, receipt)],
            rejected_routes=_rejections(
                selected=ScoutRoute.EXPLAIN,
                reproduce_reason=reproduce_rejection,
                explore_reason=explore_rejection,
                ask_reason=ask_rejection,
            ),
            input_shot_ids=list(shoot.ordered_shot_ids),
            projection_versions=_projection_versions(receipt),
            policy_version=POLICY_VERSION,
            execution_state=ScoutExecutionState.COMPLETED,
            execution_detail="The deterministic Shoot receipt is the explanation.",
            executed_at=now(),
        )
    else:
        decision = ScoutDecision(
            route=ScoutRoute.SILENCE,
            reason=(
                "This Shoot has not enough repeated or varied Evidence for useful intervention."
            ),
            warrant=[_receipt_warrant(shoot, receipt)],
            rejected_routes=_rejections(
                selected=ScoutRoute.SILENCE,
                reproduce_reason=reproduce_rejection,
                explore_reason=explore_rejection,
                ask_reason=ask_rejection,
            ),
            input_shot_ids=list(shoot.ordered_shot_ids),
            projection_versions=_projection_versions(receipt),
            policy_version=POLICY_VERSION,
            execution_state=ScoutExecutionState.COMPLETED,
            execution_detail="No intervention was delivered.",
            executed_at=now(),
        )
    await _record(ctx, shoot, decision)
    return decision


def _reproduce_decision(
    shoot: Shoot,
    receipt: ShootReceipt,
    *,
    technique_id: str,
    reference_shot_id: str,
    keeper_shot_ids: list[str],
    reason: str,
    experiment_id: str,
) -> ScoutDecision:
    return ScoutDecision(
        route=ScoutRoute.REPRODUCE,
        reason=reason,
        warrant=[
            ScoutWarrant(
                kind="keeper_technique",
                shoot_id=shoot.id,
                shoot_revision=shoot.revision,
                shot_ids=keeper_shot_ids,
                technique_id=technique_id,
                reference_shot_id=reference_shot_id,
                detail=reason,
            )
        ],
        rejected_routes=_rejections(selected=ScoutRoute.REPRODUCE),
        input_shot_ids=list(shoot.ordered_shot_ids),
        projection_versions=_projection_versions(receipt),
        policy_version=POLICY_VERSION,
        experiment_id=experiment_id,
        execution_state=ScoutExecutionState.PENDING,
    )


def _receipt_warrant(shoot: Shoot, receipt: ShootReceipt) -> ScoutWarrant:
    return ScoutWarrant(
        kind="shoot_receipt",
        shoot_id=shoot.id,
        shoot_revision=shoot.revision,
        shot_ids=list(shoot.ordered_shot_ids),
        detail=receipt.summary,
    )


def _question_techniques(
    receipt: ShootReceipt,
    missing_gear: list[str],
    deprioritized: set[str],
) -> list[taxonomy.Technique]:
    supported = []
    for figure in sorted(receipt.techniques, key=lambda item: item.technique_id):
        technique = taxonomy.BY_ID.get(figure.technique_id)
        if (
            technique is not None
            and technique.id not in deprioritized
            and figure.corroborated_shot_ids
            and route_rules.available(technique, missing_gear=missing_gear)
        ):
            supported.append(technique)
    return supported[:3]


def _ask_decision(
    shoot: Shoot,
    receipt: ShootReceipt,
    techniques: list[taxonomy.Technique],
) -> ScoutDecision:
    question = ScoutQuestion(
        id=f"scout_question_{shoot.id}_r{shoot.revision}",
        prompt="Which decision were you exploring in this Shoot?",
        options=[
            *[
                ScoutQuestionOption(
                    id=f"technique_{technique.id}",
                    label=technique.name,
                    technique_id=technique.id,
                )
                for technique in techniques
            ],
            ScoutQuestionOption(id="just_shooting", label="I was just shooting"),
        ],
    )
    warrants = [
        ScoutWarrant(
            kind="shoot_technique_choice",
            shoot_id=shoot.id,
            shoot_revision=shoot.revision,
            shot_ids=list(figure.corroborated_shot_ids),
            technique_id=figure.technique_id,
            detail=f"{figure.name} was corroborated in this Shoot.",
        )
        for figure in receipt.techniques
        if figure.technique_id in {technique.id for technique in techniques}
    ]
    return ScoutDecision(
        route=ScoutRoute.ASK,
        reason="Two or more supported decisions appeared together; Intent changes useful help.",
        warrant=warrants,
        input_shot_ids=list(shoot.ordered_shot_ids),
        projection_versions=_projection_versions(receipt),
        policy_version=POLICY_VERSION,
        question=question,
        execution_state=ScoutExecutionState.PENDING,
    )


def _explore_decision(
    shoot: Shoot,
    receipt: ShootReceipt,
    experiment: Experiment,
) -> ScoutDecision:
    baseline = experiment.baseline
    return ScoutDecision(
        route=ScoutRoute.EXPLORE,
        reason=experiment.why_now,
        warrant=[
            ScoutWarrant(
                kind="tendency_direction",
                shoot_id=shoot.id,
                shoot_revision=shoot.revision,
                shot_ids=list(experiment.warrant_shot_ids),
                technique_id=experiment.technique_id,
                detail=baseline.citation if baseline else experiment.why_now,
            )
        ],
        rejected_routes=_rejections(selected=ScoutRoute.EXPLORE),
        input_shot_ids=list(shoot.ordered_shot_ids),
        projection_versions=_projection_versions(receipt),
        policy_version=POLICY_VERSION,
        experiment_id=experiment.id,
        execution_state=ScoutExecutionState.PENDING,
    )


def _projection_versions(receipt: ShootReceipt) -> dict[str, str]:
    return {
        "shoot_receipt": receipt.calc_version,
        "tendency": tendency.CALC_VERSION,
    }


def _rejections(
    *,
    selected: ScoutRoute,
    reproduce_reason: str = "",
    explore_reason: str = "",
    ask_reason: str = "",
) -> list[ScoutRejectedRoute]:
    reasons = {
        ScoutRoute.ASK: ask_reason or "A stronger eligible route was selected.",
        ScoutRoute.EXPLORE: explore_reason or "A stronger eligible route was selected.",
        ScoutRoute.REPRODUCE: reproduce_reason or "A stronger eligible route was selected.",
        ScoutRoute.EXPLAIN: "A stronger eligible route was selected.",
        ScoutRoute.SILENCE: "Supported action or explanation is available.",
    }
    return [
        ScoutRejectedRoute(route=route, reason=reason)
        for route, reason in reasons.items()
        if route is not selected
    ]


async def _create_reproduce(
    ctx: Context,
    user: User,
    technique: taxonomy.Technique,
    pattern: experiment_scout.KeeperPattern,
    experiment_id: str,
    reason: str,
) -> Experiment | None:
    """Create the exact Reproduce action without an unconstrained writer call."""
    existing = await repo.find_experiment(ctx.store, experiment_id)
    if existing is not None:
        return existing if existing.user_id == user.id else None
    experiment = Experiment(
        id=experiment_id,
        user_id=user.id,
        technique_id=technique.id,
        type=ExperimentType.REPRODUCE,
        title=f"Repeat {technique.name}"[:60],
        brief=(
            f"Make another Shot where {technique.cue[:1].lower()}{technique.cue[1:]} "
            "Choose your own subject and moment."
        )[:2000],
        why_now=reason[:500],
        criteria=experiment_rules.criteria_for(technique, [technique.cue]),
        reference_shot_id=pattern.reference_shot_id,
        warrant_shot_ids=list(pattern.shot_ids),
        status=ExperimentStatus.OPEN,
        due_at=now() + timedelta(days=settings.experiment_ttl_days),
    )
    when = timing.deliver_at(technique.light, now(), user.last_latitude, user.last_longitude)
    experiment.deliver_at = when.at
    experiment.timing = ExperimentTiming(
        light=when.light,
        reason=when.reason,
        anchor=when.anchor,
        anchor_at=when.anchor_at,
    )
    if not await repo.create_open_experiment(ctx.store, experiment):
        return None
    await repo.record(
        ctx.store,
        user.id,
        "scout",
        "issued",
        {
            "technique_id": technique.id,
            "type": experiment.type.value,
            "title": experiment.title,
            "why": reason,
            "selection_basis": "shoot_keeper",
            "reference_shot_id": experiment.reference_shot_id,
            "hard_criteria": experiment_rules.hard_criteria_text(technique),
            "deliver_at": experiment.deliver_at.isoformat() if experiment.deliver_at else "",
            "timing": when.reason,
        },
        experiment_id=experiment.id,
    )
    return experiment


async def _record(ctx: Context, shoot: Shoot, decision: ScoutDecision) -> None:
    await repo.record_scout_decision(ctx.store, shoot, decision)
    from app.services import interventions

    await interventions.record_decision(ctx, shoot, decision)
