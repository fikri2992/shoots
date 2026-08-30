"""Typed Scout decision and action for one settled Shoot revision."""

from app.domain import scout as route_rules
from app.domain import taxonomy, tendency
from app.domain.entities import (
    Experiment,
    ExperimentType,
    InterventionAttemptState,
    ScoutDecision,
    ScoutExecutionState,
    ScoutQuestion,
    ScoutQuestionOption,
    ScoutRecommendation,
    ScoutRecommendationOption,
    ScoutRejectedRoute,
    ScoutRoute,
    ScoutWarrant,
    Shoot,
    ShootReceipt,
    SignalScope,
    now,
)
from app.infra import repository as repo
from app.services import interventions, photographer_memory
from app.services import scout as experiment_scout
from app.services.context import Context

POLICY_VERSION = "shoot-scout-4"


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
        decision.execution_detail = "Shoots found the existing Experiment for this outing."
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
    constraints = await photographer_memory.constraints_for(
        ctx,
        shoot.user_id,
        role="shoot_scout",
        purpose="shoot_intervention",
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
        reproduce_rejection = (
            "No marked Keeper has a Technique that appears clearly enough to repeat yet."
        )
    elif set(patterns) and set(patterns).issubset(deprioritized):
        reproduce_rejection = (
            "Shoots already saw two similar tries stay unchanged, so it did not offer "
            "the same Technique again."
        )
    elif technique is None:
        reproduce_rejection = (
            "Every supported Technique was offered recently or does not fit a saved constraint."
        )

    if technique is not None:
        pattern = patterns[technique.id]
        reason = (
            f"You marked {pattern.count} Shot{'s' if pattern.count != 1 else ''} with "
            f"{technique.name} as {'Keepers' if pattern.count != 1 else 'a Keeper'}. "
            "Try making that choice again on purpose."
        )
        alternatives = _shoot_explore_options(
            shoot,
            receipt,
            _recommendation_techniques(receipt, constraints.missing_gear, deprioritized),
            exclude={technique.id},
        )
        decision = _recommend_decision(
            shoot,
            receipt,
            [
                ScoutRecommendationOption(
                    id=f"reproduce_{technique.id}",
                    technique_id=technique.id,
                    technique_name=technique.name,
                    experiment_type=ExperimentType.REPRODUCE,
                    title=f"Can you make {technique.name} happen again?",
                    why_now=reason,
                    warrant_shot_ids=list(pattern.shot_ids),
                    reference_shot_id=pattern.reference_shot_id,
                ),
                *alternatives,
            ],
        )
        decision.rejected_routes = _rejections(
            selected=ScoutRoute.RECOMMEND,
            reproduce_reason=reproduce_rejection,
        )
        await _record(ctx, shoot, decision)
        return decision

    current_open = await repo.open_experiment(ctx.store, shoot.user_id)
    recommendation_techniques = _recommendation_techniques(
        receipt,
        constraints.missing_gear,
        deprioritized,
    )
    recommendation_rejection = ""
    if current_open is not None:
        recommendation_rejection = f'Experiment "{current_open.id}" already owns the open slot.'
    elif recommendation_techniques:
        decision = _recommend_decision(
            shoot,
            receipt,
            _shoot_explore_options(shoot, receipt, recommendation_techniques),
        )
        decision.rejected_routes = _rejections(
            selected=ScoutRoute.RECOMMEND,
            reproduce_reason=reproduce_rejection,
        )
        await _record(ctx, shoot, decision)
        return decision
    else:
        recommendation_rejection = "No supported Technique was clear enough to recommend."

    explore_rejection = ""
    if current_open is not None:
        explore_rejection = f'Experiment "{current_open.id}" already owns the open slot.'
    else:
        planned = await experiment_scout.plan_explore(
            ctx,
            shoot.user_id,
            experiment_id=experiment_id,
            exclude_technique_ids=deprioritized,
        )
        if planned is not None:
            decision = _recommend_decision(
                shoot,
                receipt,
                [_explore_option_from_plan(planned)],
            )
            decision.rejected_routes = _rejections(
                selected=ScoutRoute.RECOMMEND,
                reproduce_reason=reproduce_rejection,
            )
            await _record(ctx, shoot, decision)
            return decision
        explore_rejection = "No clear pattern needs an Explore right now."

    if receipt.repeated or receipt.varied:
        decision = ScoutDecision(
            route=ScoutRoute.EXPLAIN,
            reason=(
                "A clear pattern runs through this Shoot. It is worth seeing without "
                "turning it into homework."
            ),
            warrant=[_receipt_warrant(shoot, receipt)],
            rejected_routes=_rejections(
                selected=ScoutRoute.EXPLAIN,
                reproduce_reason=reproduce_rejection,
                explore_reason=explore_rejection,
                recommendation_reason=recommendation_rejection,
            ),
            input_shot_ids=list(shoot.ordered_shot_ids),
            projection_versions=_projection_versions(receipt),
            policy_version=POLICY_VERSION,
            execution_state=ScoutExecutionState.COMPLETED,
            execution_detail="Shoots found a clear pattern worth showing without adding homework.",
            executed_at=now(),
        )
    else:
        decision = ScoutDecision(
            route=ScoutRoute.SILENCE,
            reason="Nothing here is clear enough to interrupt you with yet.",
            warrant=[_receipt_warrant(shoot, receipt)],
            rejected_routes=_rejections(
                selected=ScoutRoute.SILENCE,
                reproduce_reason=reproduce_rejection,
                explore_reason=explore_rejection,
                recommendation_reason=recommendation_rejection,
            ),
            input_shot_ids=list(shoot.ordered_shot_ids),
            projection_versions=_projection_versions(receipt),
            policy_version=POLICY_VERSION,
            execution_state=ScoutExecutionState.COMPLETED,
            execution_detail="Nothing was clear enough to interrupt you with.",
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


def _recommendation_techniques(
    receipt: ShootReceipt,
    missing_gear: list[str],
    deprioritized: set[str],
) -> list[taxonomy.Technique]:
    supported = []
    figures = sorted(
        receipt.techniques,
        key=lambda item: (
            -len(set(item.corroborated_shot_ids)),
            -len(set(item.observed_shot_ids)),
            item.technique_id,
        ),
    )
    for figure in figures:
        technique = taxonomy.BY_ID.get(figure.technique_id)
        if (
            technique is not None
            and technique.id not in deprioritized
            and figure.corroborated_shot_ids
            and route_rules.available(technique, missing_gear=missing_gear)
        ):
            supported.append(technique)
    return supported[:3]


def _shoot_explore_options(
    shoot: Shoot,
    receipt: ShootReceipt,
    techniques: list[taxonomy.Technique],
    *,
    exclude: set[str] | None = None,
) -> list[ScoutRecommendationOption]:
    figures = {item.technique_id: item for item in receipt.techniques}
    options = []
    for technique in techniques:
        if technique.id in (exclude or set()):
            continue
        figure = figures[technique.id]
        count = len(set(figure.corroborated_shot_ids))
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
                warrant_shot_ids=list(figure.corroborated_shot_ids),
            )
        )
    return options


def _explore_option_from_plan(experiment: Experiment) -> ScoutRecommendationOption:
    technique = taxonomy.BY_ID[experiment.technique_id]
    return ScoutRecommendationOption(
        id=f"explore_{technique.id}",
        technique_id=technique.id,
        technique_name=technique.name,
        experiment_type=ExperimentType.EXPLORE,
        title=f"Try {technique.name} on purpose",
        why_now=experiment.why_now,
        warrant_shot_ids=list(experiment.warrant_shot_ids),
    )


def _recommend_decision(
    shoot: Shoot,
    receipt: ShootReceipt,
    options: list[ScoutRecommendationOption],
) -> ScoutDecision:
    if not options:
        raise ValueError("A Scout Recommendation needs at least one supported option")
    recommendation_id = f"scout_recommendation_{shoot.id}_r{shoot.revision}"
    warrants = [
        ScoutWarrant(
            kind=(
                "keeper_technique"
                if option.experiment_type is ExperimentType.REPRODUCE
                else "shoot_technique_direction"
            ),
            shoot_id=shoot.id,
            shoot_revision=shoot.revision,
            shot_ids=list(option.warrant_shot_ids),
            technique_id=option.technique_id,
            reference_shot_id=option.reference_shot_id,
            detail=option.why_now,
        )
        for option in options
    ]
    return ScoutDecision(
        route=ScoutRoute.RECOMMEND,
        reason=options[0].why_now,
        warrant=warrants,
        input_shot_ids=list(shoot.ordered_shot_ids),
        projection_versions=_projection_versions(receipt),
        policy_version=POLICY_VERSION,
        recommendation=ScoutRecommendation(
            id=recommendation_id,
            primary_option_id=options[0].id,
            options=options,
        ),
        execution_state=ScoutExecutionState.COMPLETED,
        execution_detail="Shoots prepared one evidence-backed Experiment idea. Nothing started.",
        attempt_state=InterventionAttemptState.OFFERED,
        executed_at=now(),
    )


def _ask_decision(
    shoot: Shoot,
    receipt: ShootReceipt,
    techniques: list[taxonomy.Technique],
) -> ScoutDecision:
    question = ScoutQuestion(
        id=f"scout_question_{shoot.id}_r{shoot.revision}",
        prompt="What were you paying attention to in this Shoot?",
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
            detail=f"{figure.name} appeared clearly in this Shoot.",
        )
        for figure in receipt.techniques
        if figure.technique_id in {technique.id for technique in techniques}
    ]
    return ScoutDecision(
        route=ScoutRoute.ASK,
        reason="Two choices kept returning. Your answer decides which one is worth exploring.",
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
    recommendation_reason: str = "",
) -> list[ScoutRejectedRoute]:
    reasons = {
        ScoutRoute.RECOMMEND: recommendation_reason or "A stronger eligible route was selected.",
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


async def _record(ctx: Context, shoot: Shoot, decision: ScoutDecision) -> None:
    await repo.record_scout_decision(ctx.store, shoot, decision)
    from app.services import interventions

    await interventions.record_decision(ctx, shoot, decision)
