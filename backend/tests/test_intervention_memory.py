"""Intervention adaptation through real Store, Experiment, and Scout seams."""

from app.domain.entities import (
    Analysis,
    Change,
    ChangeState,
    Comparability,
    Experiment,
    ExperimentStatus,
    ExperimentType,
    InterventionAttemptState,
    InterventionOutcome,
    InterventionRecord,
    ScoutDecision,
    ScoutRoute,
    ScoutWarrant,
    Shoot,
    ShootReceipt,
    Shot,
    ShotKind,
    ShotStatus,
    TechniqueEvidence,
    User,
    now,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.store import InMemoryStore
from app.services import interventions, shoot_scout
from app.services.context import Context


def context() -> Context:
    return Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)


async def test_completed_experiment_projects_comparable_outcome_without_rewriting_decision():
    ctx = context()
    user = User(id="intervention_user", email="intervention@example.test")
    await repo.put_user(ctx.store, user)
    shoot = Shoot(id="shoot_intervention", user_id=user.id, revision=1)
    decision = ScoutDecision(
        route=ScoutRoute.REPRODUCE,
        experiment_id="experiment_intervention",
        warrant=[
            ScoutWarrant(
                kind="keeper_technique",
                shoot_id=shoot.id,
                shoot_revision=1,
                technique_id="panning",
                shot_ids=["keeper_1"],
            )
        ],
        attempt_state=InterventionAttemptState.OFFERED,
    )
    original = decision.model_copy(deep=True)
    record = await interventions.record_decision(ctx, shoot, decision)
    experiment = Experiment(
        id=decision.experiment_id,
        user_id=user.id,
        technique_id="panning",
        type=ExperimentType.REPRODUCE,
        title="Repeat Panning",
        brief="Repeat the pan.",
        why_now="A Keeper supported it.",
        status=ExperimentStatus.COMPLETED,
        result_shot_ids=["result_1", "result_2"],
        change=Change(
            state=ChangeState.INSUFFICIENT,
            comparability=Comparability.TOO_FEW_SHOTS,
            outcome="Only two explicit results are available.",
        ),
    )
    await repo.put_experiment(ctx.store, experiment)

    insufficient = await interventions.refresh_for_experiment(ctx, experiment.id)
    assert insufficient.observable_outcome is InterventionOutcome.INSUFFICIENT_EVIDENCE
    assert insufficient.comparability == "too few shots"

    experiment.change = Change(
        state=ChangeState.UNCHANGED,
        comparability=Comparability.COMPARABLE,
        outcome="The comparable panning distribution did not change.",
    )
    await repo.put_experiment(ctx.store, experiment)
    refreshed = await interventions.refresh_for_experiment(ctx, experiment.id)

    assert refreshed.id == record.id
    assert refreshed.attempt_state is InterventionAttemptState.COMPLETED
    assert refreshed.observable_outcome is InterventionOutcome.UNCHANGED
    assert refreshed.result_shot_ids == ["result_1", "result_2"]
    assert refreshed.outcome_reason == experiment.change.outcome
    assert decision == original


async def test_two_comparable_unchanged_outcomes_deprioritize_only_automatic_route():
    ctx = context()
    user = User(id="adapt_user", email="adapt@example.test")
    await repo.put_user(ctx.store, user)
    keeper = Shot(
        id="keeper_pan",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        filename="keeper.jpg",
        mime_type="image/jpeg",
        status=ShotStatus.ANALYZED,
        kept_at=now(),
    )
    await repo.put_shot(ctx.store, keeper)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=keeper.id,
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="panning",
                    confidence=0.9,
                    agreement=2,
                )
            ],
        ),
    )
    for revision in (1, 2):
        await repo.put_intervention(
            ctx.store,
            InterventionRecord(
                id=f"intervention_old_{revision}",
                user_id=user.id,
                shoot_id=f"old_shoot_{revision}",
                shoot_revision=revision,
                route=ScoutRoute.REPRODUCE,
                technique_id="panning",
                attempt_state=InterventionAttemptState.COMPLETED,
                observable_outcome=InterventionOutcome.UNCHANGED,
                outcome_reason="Comparable behaviour remained unchanged.",
            ),
        )
    current = Shoot(id="shoot_current", user_id=user.id, ordered_shot_ids=[keeper.id])
    receipt = ShootReceipt(
        calc_version="receipt-adapt",
        summary="Panning appeared again.",
        shot_count=1,
        scene_count=1,
        readable_shot_count=1,
        repeated=["Panning appeared again."],
    )

    decision = await shoot_scout.decide(ctx, current, receipt)

    assert decision.route is not ScoutRoute.REPRODUCE
    rejected = {item.route: item.reason for item in decision.rejected_routes}
    assert "two comparable unchanged outcomes" in rejected[ScoutRoute.REPRODUCE].lower()
    assert await interventions.deprioritized_technique_ids(ctx, user.id) == {"panning"}
