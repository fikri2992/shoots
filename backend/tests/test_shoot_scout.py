"""Shoot-level Scout decisions through real Store and service seams."""

from datetime import UTC, datetime, timedelta

from app.domain.entities import (
    Analysis,
    Composition,
    Criteria,
    Experiment,
    ExperimentType,
    GridSpec,
    RunStage,
    ScoutExecutionState,
    ScoutRoute,
    Shoot,
    ShootReceipt,
    Shot,
    ShotKind,
    ShotSource,
    TechniqueEvidence,
    Tone,
    User,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.store import InMemoryStore
from app.services import runs, shoot_scout, shoots
from app.services.context import Context


def context() -> Context:
    return Context(
        store=InMemoryStore(),
        blobs=None,
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )


async def add_readable_shot(
    ctx: Context,
    *,
    shot_id: str,
    captured_at: datetime,
    kept: bool = False,
    technique_id: str = "",
) -> Shot:
    shot = Shot(
        id=shot_id,
        user_id="scout_user",
        kind=ShotKind.PHOTO,
        source=ShotSource.ANDROID,
        source_id=f"camera:{shot_id}",
        filename=f"{shot_id}.jpg",
        mime_type="image/jpeg",
        captured_at=captured_at,
        kept_at=captured_at if kept else None,
        grid=GridSpec(cols=7, rows=7, width=1200, height=1600),
        tone=Tone(luma_mean=0.4, warm_share=30, cool_share=10),
    )
    await repo.put_shot(ctx.store, shot)
    evidence = (
        [TechniqueEvidence(technique_id=technique_id, confidence=0.9, agreement=2)]
        if technique_id
        else []
    )
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=shot.user_id,
            model="reader-v1",
            prompt_version="prompt-v1",
            composition=Composition(
                subject_x=0.5,
                subject_y=0.5,
                subject_cells=["D4", "D5", "E4", "E5"],
            ),
            techniques=evidence,
        ),
    )
    await shoots.observe_shot(ctx, shot.id)
    await runs.ensure(ctx, shot)
    for stage in RunStage:
        await runs.completed(ctx, shot.id, stage, f"{stage.value} settled")
    return shot


async def test_useful_shoot_without_keeper_direction_routes_to_explain():
    ctx = context()
    await repo.put_user(ctx.store, User(id="scout_user", email="scout@example.test"))
    start = datetime(2026, 8, 26, 8, 0, tzinfo=UTC)
    first = await add_readable_shot(ctx, shot_id="explain_1", captured_at=start)
    await add_readable_shot(
        ctx,
        shot_id="explain_2",
        captured_at=start + timedelta(minutes=1),
    )
    membership = await shoots.observe_shot(ctx, first.id)

    await shoots.close_inactive(ctx, start + timedelta(hours=1))

    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None
    assert record.scout.route is ScoutRoute.EXPLAIN
    assert record.scout.execution_state is ScoutExecutionState.COMPLETED
    assert record.scout.input_shot_ids == ["explain_1", "explain_2"]
    assert record.scout.projection_versions["shoot_receipt"] == record.receipt.calc_version
    assert record.scout.warrant[0].shoot_id == membership.shoot_id
    rejected = {item.route: item.reason for item in record.scout.rejected_routes}
    assert "marked Keeper" in rejected[ScoutRoute.REPRODUCE]
    assert "No supported Tendency Direction" in rejected[ScoutRoute.EXPLORE]
    assert "Fewer than two" in rejected[ScoutRoute.ASK]
    assert await repo.open_experiment(ctx.store, "scout_user") is None


async def test_supported_tendency_without_keeper_offers_corrected_explore():
    ctx = context()
    await repo.put_user(ctx.store, User(id="scout_user", email="scout@example.test"))
    start = datetime(2026, 8, 26, 8, 30, tzinfo=UTC)
    first = None
    for index in range(8):
        shot = await add_readable_shot(
            ctx,
            shot_id=f"explore_{index}",
            captured_at=start + timedelta(minutes=index),
        )
        first = first or shot
    assert first is not None
    membership = await shoots.observe_shot(ctx, first.id)

    await shoots.close_inactive(ctx, start + timedelta(hours=1))

    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None
    assert record.scout.route is ScoutRoute.EXPLORE
    assert record.scout.execution_state is ScoutExecutionState.COMPLETED
    assert record.scout.policy_version == "shoot-scout-3"
    experiment = await repo.get_experiment(ctx.store, record.scout.experiment_id)
    assert experiment.type is ExperimentType.EXPLORE
    assert len(experiment.variations) == 3
    assert experiment.criteria.text == []
    assert experiment.verdicts == []
    assert experiment.baseline is not None
    assert record.scout.warrant[0].kind == "tendency_direction"


async def test_sparse_shoot_records_evidenced_silence():
    ctx = context()
    await repo.put_user(ctx.store, User(id="scout_user", email="scout@example.test"))
    start = datetime(2026, 8, 26, 9, 0, tzinfo=UTC)
    shot = await add_readable_shot(ctx, shot_id="silent_1", captured_at=start)
    membership = await shoots.observe_shot(ctx, shot.id)

    await shoots.close_inactive(ctx, start + timedelta(hours=1))

    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None
    assert record.scout.route is ScoutRoute.SILENCE
    assert "not enough repeated or varied Evidence" in record.scout.reason
    assert record.scout.execution_state is ScoutExecutionState.COMPLETED


async def test_keeper_backed_shoot_creates_one_deterministic_reproduce():
    ctx = context()
    await repo.put_user(ctx.store, User(id="scout_user", email="scout@example.test"))
    start = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    shot = await add_readable_shot(
        ctx,
        shot_id="reproduce_keeper",
        captured_at=start,
        kept=True,
        technique_id="backlight",
    )
    membership = await shoots.observe_shot(ctx, shot.id)

    await shoots.close_inactive(ctx, start + timedelta(hours=1))

    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None
    assert record.scout.route is ScoutRoute.REPRODUCE
    assert record.scout.execution_state is ScoutExecutionState.COMPLETED
    assert record.scout.experiment_id == f"experiment_{membership.shoot_id}_r1"
    experiment = await repo.get_experiment(ctx.store, record.scout.experiment_id)
    assert experiment.type is ExperimentType.REPRODUCE
    assert experiment.technique_id == "backlight"
    assert experiment.reference_shot_id == shot.id
    assert experiment.warrant_shot_ids == [shot.id]
    assert experiment.criteria.vision == ["backlight"]
    assert "1 marked Keeper" in experiment.why_now

    replay = await shoots.on_run_settled(ctx, shot.id)
    assert replay == record
    experiments = await repo.list_experiments(ctx.store, shot.user_id)
    assert [item.id for item in experiments] == [record.scout.experiment_id]
    events = await repo.list_events(ctx.store, shot.user_id)
    assert sum(event.stage == "shoot_decision" for event in events) == 1


async def test_existing_open_experiment_rejects_second_reproduce_but_keeps_receipt():
    ctx = context()
    await repo.put_user(ctx.store, User(id="scout_user", email="scout@example.test"))
    existing = Experiment(
        id="existing_experiment",
        user_id="scout_user",
        technique_id="rule_of_thirds",
        type=ExperimentType.REPRODUCE,
        title="Existing",
        brief="Already open",
        why_now="Earlier evidence",
        criteria=Criteria(vision=["rule_of_thirds"]),
        reference_shot_id="older_keeper",
    )
    assert await repo.create_open_experiment(ctx.store, existing)
    start = datetime(2026, 8, 26, 11, 0, tzinfo=UTC)
    first = await add_readable_shot(
        ctx,
        shot_id="held_keeper_1",
        captured_at=start,
        kept=True,
        technique_id="backlight",
    )
    await add_readable_shot(
        ctx,
        shot_id="held_keeper_2",
        captured_at=start + timedelta(minutes=1),
    )
    membership = await shoots.observe_shot(ctx, first.id)

    await shoots.close_inactive(ctx, start + timedelta(hours=1))

    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None
    assert record.scout.route is ScoutRoute.EXPLAIN
    rejected = {item.route: item.reason for item in record.scout.rejected_routes}
    assert existing.id in rejected[ScoutRoute.REPRODUCE]
    assert (await repo.open_experiment(ctx.store, "scout_user")).id == existing.id
    assert len(await repo.list_experiments(ctx.store, "scout_user")) == 1


async def test_replay_recovers_the_same_deterministic_experiment_and_exact_warrant():
    ctx = context()
    await repo.put_user(ctx.store, User(id="scout_user", email="scout@example.test"))
    shoot = Shoot(
        id="shoot_recovery",
        user_id="scout_user",
        revision=2,
        ordered_shot_ids=["current_1", "current_2"],
    )
    receipt = ShootReceipt(
        calc_version="shoot-receipt-1+tendency-2",
        summary="2 Shots across 1 Scene.",
        repeated=["2 of 2 readable Shots used centred placement."],
    )
    experiment = Experiment(
        id="experiment_shoot_recovery_r2",
        user_id="scout_user",
        technique_id="backlight",
        type=ExperimentType.REPRODUCE,
        title="Repeat Backlight",
        brief="Repeat the decision.",
        why_now="2 marked Keepers include Backlight.",
        criteria=Criteria(vision=["backlight"]),
        reference_shot_id="keeper_2",
        warrant_shot_ids=["keeper_1", "keeper_2"],
    )
    assert await repo.create_open_experiment(ctx.store, experiment)

    first = await shoot_scout.decide(ctx, shoot, receipt)
    replay = await shoot_scout.decide(ctx, shoot, receipt)

    assert first.route is ScoutRoute.REPRODUCE
    assert replay.route is ScoutRoute.REPRODUCE
    assert first.experiment_id == replay.experiment_id == experiment.id
    assert first.warrant[0].shot_ids == ["keeper_1", "keeper_2"]
    assert replay.warrant[0].shot_ids == ["keeper_1", "keeper_2"]
    assert len(await repo.list_experiments(ctx.store, "scout_user")) == 1
    events = await repo.list_events(ctx.store, "scout_user")
    assert sum(event.stage == "shoot_decision" for event in events) == 1
