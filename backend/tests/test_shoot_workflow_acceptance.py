"""Continuous acceptance of the Shoot learning work unit."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    Analysis,
    CaptureSession,
    CaptureSessionMember,
    Composition,
    Criteria,
    Experiment,
    ExperimentStatus,
    ExperimentType,
    GridSpec,
    RunStage,
    ScoutRoute,
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
from app.services import runs, shoots
from app.services.context import Context


async def readable_shot(
    ctx: Context,
    *,
    shot_id: str,
    captured_at: datetime,
    kept: bool = False,
    capture_session_id: str = "",
    experiment_id: str = "",
) -> Shot:
    shot = Shot(
        id=shot_id,
        user_id="acceptance_user",
        kind=ShotKind.PHOTO,
        source=ShotSource.ANDROID,
        source_id=f"device:external:{shot_id}:{int(captured_at.timestamp())}:4096",
        filename=f"{shot_id}.jpg",
        mime_type="image/jpeg",
        captured_at=captured_at,
        kept_at=captured_at if kept else None,
        capture_session_id=capture_session_id,
        experiment_id=experiment_id,
        grid=GridSpec(cols=7, rows=7, width=1200, height=1600),
        tone=Tone(luma_mean=0.4, warm_share=30, cool_share=10),
    )
    await repo.put_shot(ctx.store, shot)
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
            techniques=[
                TechniqueEvidence(
                    technique_id="backlight",
                    confidence=0.9,
                    agreement=2,
                )
            ],
        ),
    )
    await shoots.observe_shot(ctx, shot.id)
    return shot


async def completed_run(ctx: Context, shot: Shot) -> None:
    await runs.ensure(ctx, shot)
    for stage in RunStage:
        await runs.completed(ctx, shot.id, stage, f"{stage.value} settled")


async def test_one_camera_period_becomes_a_revisioned_learning_record_and_action():
    ctx = Context(
        store=InMemoryStore(),
        blobs=None,
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user = User(id="acceptance_user", email="acceptance@example.test")
    await repo.put_user(ctx.store, user)
    old_experiment = Experiment(
        id="older_experiment",
        user_id=user.id,
        technique_id="rule_of_thirds",
        type=ExperimentType.REPRODUCE,
        title="Earlier Experiment",
        brief="An older explicit batch.",
        why_now="Earlier evidence",
        criteria=Criteria(vision=["rule_of_thirds"]),
        reference_shot_id="older_keeper",
        status=ExperimentStatus.COMPLETED,
    )
    await repo.put_experiment(ctx.store, old_experiment)
    start = datetime(2026, 8, 27, 8, 0, tzinfo=UTC)
    shared = await readable_shot(
        ctx,
        shot_id="shared_result",
        captured_at=start + timedelta(minutes=2),
        capture_session_id="capture_old",
        experiment_id=old_experiment.id,
    )
    session = CaptureSession(
        id=shared.capture_session_id,
        user_id=user.id,
        experiment_id=old_experiment.id,
        device_id="device",
        expires_at=start + timedelta(hours=2),
    )
    assert await repo.create_capture_session(ctx.store, session)
    await repo.commit_capture_session(
        ctx.store,
        session.id,
        [CaptureSessionMember(source_id=shared.source_id, order=0, shot_id=shared.id)],
        start,
    )
    keeper = await readable_shot(
        ctx,
        shot_id="keeper_free",
        captured_at=start,
        kept=True,
    )
    terminal = Shot(
        id="terminal_member",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        source=ShotSource.ANDROID,
        source_id=f"device:external:terminal:{int((start + timedelta(minutes=10)).timestamp())}:12",
        filename="terminal.heic",
        mime_type="image/heic",
        captured_at=start + timedelta(minutes=10),
    )
    await repo.put_shot(ctx.store, terminal)
    terminal_membership = await shoots.observe_shot(ctx, terminal.id)
    await completed_run(ctx, keeper)
    await completed_run(ctx, shared)
    await runs.ensure(ctx, terminal)
    await runs.terminal(ctx, terminal.id, RunStage.ANALYST, "unsupported media")

    await shoots.close_inactive(ctx, start + timedelta(hours=1))

    first = await repo.find_shoot_record(ctx.store, terminal_membership.shoot_id, 1)
    assert first is not None
    assert first.shot_ids == [keeper.id, shared.id, terminal.id]
    assert first.receipt.scene_count == 2
    assert first.receipt.shots_per_scene == [2, 1]
    assert first.receipt.unreadable_shot_ids == [terminal.id]
    assert first.scout.route is ScoutRoute.REPRODUCE
    assert first.scout.warrant[0].reference_shot_id == keeper.id
    assert first.scout.warrant[0].shot_ids == [keeper.id]
    offered = await repo.get_experiment(ctx.store, first.scout.experiment_id)
    assert offered.reference_shot_id == keeper.id
    assert offered.type is ExperimentType.REPRODUCE
    assert "overall_score" not in first.receipt.model_dump()

    late = await readable_shot(
        ctx,
        shot_id="late_free",
        captured_at=start + timedelta(minutes=3),
    )
    late_membership = await shoots.observe_shot(ctx, late.id)
    assert late_membership.shoot_id == terminal_membership.shoot_id
    assert late_membership.shoot_revision == 2
    await completed_run(ctx, late)

    second = await repo.find_shoot_record(ctx.store, terminal_membership.shoot_id, 2)
    assert second is not None
    assert second.shot_ids == [keeper.id, shared.id, late.id, terminal.id]
    assert second.scout.route is ScoutRoute.EXPLAIN
    assert first.shot_ids == [keeper.id, shared.id, terminal.id]
    assert first.scene_ids != second.scene_ids

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            snapshot = client.get("/api/mobile/snapshot")
            assert snapshot.status_code == 200, snapshot.text
            body = snapshot.json()
            assert body["latest_shoot"]["revision"] == 2
            assert body["latest_shoot_record"]["revision"] == 2
            assert body["latest_shoot_record"]["scout"]["route"] == "explain"
    finally:
        main.app.dependency_overrides.clear()

    replay = await shoots.on_run_settled(ctx, late.id)
    assert replay == second
    events = await repo.list_events(ctx.store, user.id)
    assert sum(event.stage == "shoot_settled" for event in events) == 2
    assert sum(event.stage == "shoot_decision" for event in events) == 2
    assert len(await repo.list_experiments(ctx.store, user.id)) == 2
