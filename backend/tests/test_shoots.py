"""Scene and Shoot behaviour through the real module and Store seam."""

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.config import settings
from app.domain.entities import (
    Analysis,
    CaptureSession,
    CaptureSessionMember,
    CaptureSessionStatus,
    Composition,
    GridSpec,
    RunStage,
    RunStepState,
    ShootStatus,
    Shot,
    ShotKind,
    ShotSource,
    TechniqueEvidence,
    Tone,
    User,
    now,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import runs, shoots
from app.services.context import Context
from tests.fixtures import jpeg_with_exif


def context() -> Context:
    return Context(
        store=InMemoryStore(),
        blobs=None,
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )


async def camera_shot(ctx: Context, shot_id: str, captured_at: datetime) -> Shot:
    if await repo.find_user(ctx.store, "shoot_user") is None:
        await repo.put_user(
            ctx.store,
            User(id="shoot_user", email="shoot-user@example.test"),
        )
    shot = Shot(
        id=shot_id,
        user_id="shoot_user",
        kind=ShotKind.PHOTO,
        source=ShotSource.ANDROID,
        source_id=f"camera:{shot_id}",
        filename=f"{shot_id}.jpg",
        mime_type="image/jpeg",
        captured_at=captured_at,
    )
    await repo.put_shot(ctx.store, shot)
    return shot


async def settle_run(ctx: Context, shot: Shot) -> None:
    await runs.ensure(ctx, shot)
    for stage in RunStage:
        await runs.completed(ctx, shot.id, stage, f"{stage.value} settled")


async def test_observing_camera_shots_groups_scenes_inside_natural_shoot():
    ctx = context()
    start = datetime(2026, 8, 26, 8, 0, tzinfo=UTC)
    first = await camera_shot(ctx, "shot_first", start)
    second = await camera_shot(ctx, "shot_second", start + timedelta(minutes=2))
    third = await camera_shot(ctx, "shot_third", start + timedelta(minutes=10))
    later = await camera_shot(ctx, "shot_later", start + timedelta(hours=1))

    first_membership = await shoots.observe_shot(ctx, first.id)
    second_membership = await shoots.observe_shot(ctx, second.id)
    third_membership = await shoots.observe_shot(ctx, third.id)
    later_membership = await shoots.observe_shot(ctx, later.id)

    assert first_membership.shoot_id == second_membership.shoot_id
    assert second_membership.shoot_id == third_membership.shoot_id
    assert first_membership.scene_id == second_membership.scene_id
    assert third_membership.scene_id != first_membership.scene_id
    assert later_membership.shoot_id != first_membership.shoot_id

    stored = await repo.get_shoot(ctx.store, first_membership.shoot_id)
    assert stored.ordered_shot_ids == [first.id, second.id, third.id]
    assert stored.ordered_scene_ids == [first_membership.scene_id, third_membership.scene_id]


async def test_late_arrival_keeps_capture_order_and_replay_is_a_noop():
    ctx = context()
    start = datetime(2026, 8, 26, 9, 0, tzinfo=UTC)
    first = await camera_shot(ctx, "shot_one", start)
    second = await camera_shot(ctx, "shot_two", start + timedelta(minutes=2))
    third = await camera_shot(ctx, "shot_three", start + timedelta(minutes=10))

    first_membership = await shoots.observe_shot(ctx, first.id)
    third_membership = await shoots.observe_shot(ctx, third.id)
    second_membership = await shoots.observe_shot(ctx, second.id)
    replayed = await shoots.observe_shot(ctx, second.id)

    assert first_membership.shoot_id == third_membership.shoot_id
    assert second_membership == replayed
    assert second_membership.scene_id == first_membership.scene_id

    stored = await repo.get_shoot(ctx.store, first_membership.shoot_id)
    assert stored.ordered_shot_ids == [first.id, second.id, third.id]
    assert stored.ordered_scene_ids == [first_membership.scene_id, third_membership.scene_id]
    first_scene = await repo.get_scene(ctx.store, first_membership.scene_id)
    assert first_scene.ordered_shot_ids == [first.id, second.id]


async def test_concurrent_camera_arrivals_share_one_scene_and_shoot():
    ctx = context()
    start = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    first = await camera_shot(ctx, "shot_concurrent_one", start)
    second = await camera_shot(ctx, "shot_concurrent_two", start + timedelta(seconds=10))

    memberships = await asyncio.gather(
        shoots.observe_shot(ctx, first.id),
        shoots.observe_shot(ctx, second.id),
    )

    assert memberships[0].shoot_id == memberships[1].shoot_id
    assert memberships[0].scene_id == memberships[1].scene_id
    stored_shoots = await repo.list_shoots(ctx.store, first.user_id)
    assert len(stored_shoots) == 1
    assert stored_shoots[0].ordered_shot_ids == [first.id, second.id]


async def test_phone_ingress_automatically_observes_the_camera_shot(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "shoot_ingress_user"
    await repo.put_user(ctx.store, User(id=user_id, email="shoot@example.test"))
    captured_at = datetime(2026, 8, 26, 11, 30, tzinfo=UTC)
    source_id = f"device-1:external:301:{int(captured_at.timestamp())}:2048"
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id, "device_id": "device-1"}

    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/api/ingress/shots",
                files={"file": ("IMG_301.jpg", jpeg_with_exif(), "image/jpeg")},
                data={"source_id": source_id},
            )
            assert response.status_code == 200, response.text
    finally:
        main.app.dependency_overrides.clear()

    stored_shoots = await repo.list_shoots(ctx.store, user_id)
    assert len(stored_shoots) == 1
    assert stored_shoots[0].device_id == "device-1"
    assert stored_shoots[0].started_at == captured_at
    assert stored_shoots[0].ordered_shot_ids == [response.json()["shot_id"]]


async def test_closing_shoot_waits_for_every_member_run_then_settles_once():
    ctx = context()
    start = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    first = await camera_shot(ctx, "shot_barrier_one", start)
    second = await camera_shot(ctx, "shot_barrier_two", start + timedelta(minutes=2))
    membership = await shoots.observe_shot(ctx, first.id)
    await shoots.observe_shot(ctx, second.id)
    await runs.ensure(ctx, first)
    await runs.ensure(ctx, second)

    await shoots.close_inactive(ctx, start + timedelta(hours=1))

    closing = await repo.get_shoot(ctx.store, membership.shoot_id)
    assert closing.status is ShootStatus.CLOSING
    assert await repo.find_shoot_record(ctx.store, closing.id, closing.revision) is None

    await settle_run(ctx, first)
    assert await repo.find_shoot_record(ctx.store, closing.id, closing.revision) is None

    await settle_run(ctx, second)
    record = await repo.find_shoot_record(ctx.store, closing.id, closing.revision)
    assert record is not None
    assert record.shot_ids == [first.id, second.id]
    assert record.run_outcomes == {first.id: "completed", second.id: "completed"}

    settled = await repo.get_shoot(ctx.store, membership.shoot_id)
    assert settled.status is ShootStatus.SETTLED
    assert settled.current_record_revision == 1
    replayed = await shoots.on_run_settled(ctx, second.id)
    assert replayed == record
    events = await repo.list_events(ctx.store, first.user_id)
    assert sum(event.stage == "shoot_settled" for event in events) == 1


async def test_frequent_task_closes_inactive_shoots_without_pipeline_buttons(monkeypatch):
    ctx = context()
    user = User(id="shoot_tick_user", email="tick@example.test")
    await repo.put_user(ctx.store, user)
    shot = Shot(
        id="shot_tick",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        source=ShotSource.ANDROID,
        source_id="device-tick:external:401:1:2048",
        filename="tick.jpg",
        mime_type="image/jpeg",
        captured_at=now() - timedelta(hours=2),
    )
    await repo.put_shot(ctx.store, shot)
    membership = await shoots.observe_shot(ctx, shot.id)
    await settle_run(ctx, shot)
    assert await repo.find_shoot_record(ctx.store, membership.shoot_id, 1) is None

    monkeypatch.setattr(settings, "tasks_token", "test-shoot-token")
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/tasks/tick",
                headers={"X-Tasks-Token": "test-shoot-token"},
            )
            assert response.status_code == 200, response.text
            assert response.json()["shoots_closed"] == 1
    finally:
        main.app.dependency_overrides.clear()

    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None


async def test_frequent_task_recovers_a_closing_shoot_after_interrupted_settlement():
    ctx = context()
    start = datetime(2026, 8, 26, 13, 0, tzinfo=UTC)
    shot = await camera_shot(ctx, "shot_recover_closing", start)
    membership = await shoots.observe_shot(ctx, shot.id)
    await runs.ensure(ctx, shot)
    closing, changed = await repo.mark_shoot_closing(ctx.store, membership.shoot_id)
    assert changed and closing.status is ShootStatus.CLOSING
    run = await repo.find_run_for_shot(ctx.store, shot.id)
    assert run is not None
    for stage in RunStage:
        await repo.advance_run(
            ctx.store,
            run.id,
            stage,
            RunStepState.COMPLETED,
            f"{stage.value} settled outside callback",
        )

    await shoots.close_inactive(ctx, start + timedelta(hours=1))

    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None
    assert (await repo.get_shoot(ctx.store, membership.shoot_id)).status is ShootStatus.SETTLED


async def test_late_camera_shot_versions_a_settled_shoot_without_rewriting_history():
    ctx = context()
    start = datetime(2026, 8, 26, 14, 0, tzinfo=UTC)
    first = await camera_shot(ctx, "shot_revision_one", start)
    membership = await shoots.observe_shot(ctx, first.id)
    await settle_run(ctx, first)
    await shoots.close_inactive(ctx, start + timedelta(hours=1))
    original = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert original is not None
    assert original.shot_ids == [first.id]

    late = await camera_shot(ctx, "shot_revision_late", start + timedelta(minutes=2))
    late_membership = await shoots.observe_shot(ctx, late.id)

    assert late_membership.shoot_id == membership.shoot_id
    assert late_membership.shoot_revision == 2
    revised = await repo.get_shoot(ctx.store, membership.shoot_id)
    assert revised.status is ShootStatus.CLOSING
    assert revised.current_record_revision == 2
    assert await repo.find_shoot_record(ctx.store, membership.shoot_id, 2) is None
    assert original == await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)

    await settle_run(ctx, late)
    current = await repo.find_shoot_record(ctx.store, membership.shoot_id, 2)
    assert current is not None
    assert current.shot_ids == [first.id, late.id]
    assert original.shot_ids == [first.id]
    assert current.scene_ids != original.scene_ids

    replayed = await shoots.observe_shot(ctx, late.id)
    assert replayed.shoot_revision == 2
    assert len(await repo.list_shoots(ctx.store, first.user_id)) == 1


async def test_shoot_settlement_does_not_wait_for_capture_session_evaluation():
    ctx = context()
    start = datetime(2026, 8, 26, 15, 0, tzinfo=UTC)
    shot = await camera_shot(ctx, "shot_shared_run", start)
    shot.capture_session_id = "capture_shared_run"
    await repo.put_shot(ctx.store, shot)
    membership = await shoots.observe_shot(ctx, shot.id)
    session = CaptureSession(
        id=shot.capture_session_id,
        user_id=shot.user_id,
        experiment_id="experiment_shared_run",
        device_id="device-1",
        expires_at=start + timedelta(hours=2),
    )
    assert await repo.create_capture_session(ctx.store, session)
    await repo.commit_capture_session(
        ctx.store,
        session.id,
        [CaptureSessionMember(source_id=shot.source_id, order=0, shot_id=shot.id)],
        start,
    )
    await shoots.close_inactive(ctx, start + timedelta(hours=1))

    await settle_run(ctx, shot)

    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None
    assert record.shot_ids == [shot.id]
    capture_session = await repo.get_capture_session(ctx.store, session.id)
    assert capture_session.status is CaptureSessionStatus.COMMITTED
    assert capture_session.evaluated_at is None


async def test_terminal_run_is_counted_as_unreadable_and_does_not_block_shoot():
    ctx = context()
    start = datetime(2026, 8, 26, 16, 0, tzinfo=UTC)
    readable = await camera_shot(ctx, "shot_readable", start)
    unreadable = await camera_shot(ctx, "shot_unreadable", start + timedelta(minutes=1))
    membership = await shoots.observe_shot(ctx, readable.id)
    await shoots.observe_shot(ctx, unreadable.id)
    await settle_run(ctx, readable)
    await runs.ensure(ctx, unreadable)
    await shoots.close_inactive(ctx, start + timedelta(hours=1))

    await runs.terminal(
        ctx,
        unreadable.id,
        RunStage.ANALYST,
        "unsupported media",
    )

    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None
    assert record.run_outcomes == {
        readable.id: "completed",
        unreadable.id: "terminal",
    }
    assert record.unreadable_shot_ids == [unreadable.id]


async def test_settled_shoot_receipt_reports_exact_decisions_and_blind_spots():
    ctx = context()
    start = datetime(2026, 8, 26, 17, 0, tzinfo=UTC)
    first = await camera_shot(ctx, "shot_receipt_one", start)
    second = await camera_shot(ctx, "shot_receipt_two", start + timedelta(minutes=2))
    third = await camera_shot(ctx, "shot_receipt_three", start + timedelta(minutes=9))
    for shot, x, width, height, warm, cool in (
        (first, 0.5, 1200, 1600, 36.0, 10.0),
        (second, 0.52, 1200, 1600, 30.0, 12.0),
        (third, 0.52, 1600, 1200, 8.0, 34.0),
    ):
        shot.grid = GridSpec(cols=7, rows=7, width=width, height=height)
        shot.tone = Tone(luma_mean=0.45, warm_share=warm, cool_share=cool)
        shot.kept_at = start if shot is first else None
        await repo.put_shot(ctx.store, shot)
        await repo.put_analysis(
            ctx.store,
            Analysis(
                shot_id=shot.id,
                user_id=shot.user_id,
                model="reader-v1",
                prompt_version="prompt-v1",
                composition=Composition(
                    subject_x=x,
                    subject_y=0.5,
                    subject_cells=["D4", "D5", "E4", "E5"],
                ),
                techniques=[
                    TechniqueEvidence(
                        technique_id="backlight",
                        confidence=0.9,
                        agreement=2 if shot is not third else 1,
                    )
                ],
            ),
        )
        await shoots.observe_shot(ctx, shot.id)
        await settle_run(ctx, shot)

    membership = await shoots.observe_shot(ctx, first.id)
    await shoots.close_inactive(ctx, start + timedelta(hours=1))

    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None
    assert record.provenance.shot_ids == [first.id, second.id, third.id]
    assert record.provenance.sample_size == 3
    assert record.provenance.calc_version == "shoot-receipt-1+tendency-2"
    assert record.receipt.shot_count == 3
    assert record.receipt.scene_count == 2
    assert record.receipt.shots_per_scene == [2, 1]
    assert record.receipt.readable_shot_count == 3
    assert record.receipt.keeper_shot_ids == [first.id]
    assert "overall_score" not in record.receipt.model_dump()
    assert record.deconstruction.status.value == "needs_cover"
    assert record.deconstruction.deconstruction_id
    drafts = await repo.list_deconstructions(ctx.store, first.user_id)
    assert [draft.id for draft in drafts] == [record.deconstruction.deconstruction_id]

    placement = next(item for item in record.receipt.dimensions if item.dimension_id == "placement")
    assert placement.authority == "model_read"
    assert placement.counts == {"centred": 3}
    assert any(
        "3 of 3" in line and "centred" in line.lower() for line in record.receipt.repeated
    )
    assert any("portrait" in line and "landscape" in line for line in record.receipt.varied)
    assert any("height" in item.lower() for item in record.receipt.blind_spots)

    technique = next(item for item in record.receipt.techniques if item.technique_id == "backlight")
    assert technique.observed_shot_ids == [first.id, second.id, third.id]
    assert technique.corroborated_shot_ids == [first.id, second.id]
    assert technique.authority == "model_read"


async def test_shoot_receipt_preserves_terminal_coverage_and_analysis_versions():
    ctx = context()
    start = datetime(2026, 8, 26, 18, 0, tzinfo=UTC)
    readable = await camera_shot(ctx, "shot_receipt_readable", start)
    readable.grid = GridSpec(cols=7, rows=7, width=1200, height=1600)
    readable.tone = Tone(luma_mean=0.3, warm_share=20, cool_share=20)
    await repo.put_shot(ctx.store, readable)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=readable.id,
            user_id=readable.user_id,
            model="reader-v2",
            prompt_version="prompt-v2",
            composition=Composition(subject_x=0.5, subject_y=0.5),
        ),
    )
    unreadable = await camera_shot(
        ctx,
        "shot_receipt_terminal",
        start + timedelta(minutes=1),
    )
    membership = await shoots.observe_shot(ctx, readable.id)
    await shoots.observe_shot(ctx, unreadable.id)
    await settle_run(ctx, readable)
    await runs.ensure(ctx, unreadable)
    await shoots.close_inactive(ctx, start + timedelta(hours=1))
    await runs.terminal(ctx, unreadable.id, RunStage.ANALYST, "unsupported media")

    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None
    assert record.receipt.shot_count == 2
    assert record.receipt.readable_shot_count == 1
    assert record.receipt.unreadable_shot_ids == [unreadable.id]
    assert record.provenance.analysis_versions.keys() == {readable.id}
    assert record.provenance.inputs[0].model == "reader-v2"


async def test_terminal_external_stage_does_not_erase_a_completed_analysis():
    ctx = context()
    start = datetime(2026, 8, 26, 18, 30, tzinfo=UTC)
    shot = await camera_shot(ctx, "shot_terminal_after_read", start)
    shot.grid = GridSpec(cols=7, rows=7, width=1200, height=1600)
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=shot.user_id,
            model="reader-v2",
            prompt_version="prompt-v2",
            composition=Composition(subject_x=0.5, subject_y=0.5),
        ),
    )
    membership = await shoots.observe_shot(ctx, shot.id)
    await runs.ensure(ctx, shot)
    await shoots.close_inactive(ctx, start + timedelta(hours=1))

    await runs.terminal(ctx, shot.id, RunStage.SCRIBE, "Drive unavailable")

    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None
    assert record.run_outcomes == {shot.id: "terminal"}
    assert record.unreadable_shot_ids == []
    assert record.receipt.readable_shot_count == 1


async def _settled_record_for_analysis(subject_x: float):
    ctx = context()
    start = datetime(2026, 8, 26, 19, 0, tzinfo=UTC)
    shot = await camera_shot(ctx, "shot_analysis_version", start)
    shot.grid = GridSpec(cols=7, rows=7, width=1200, height=1600)
    shot.tone = Tone(luma_mean=0.5, warm_share=20, cool_share=20)
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=shot.user_id,
            model="reader-v1",
            prompt_version="prompt-v1",
            composition=Composition(subject_x=subject_x, subject_y=0.5),
        ),
    )
    membership = await shoots.observe_shot(ctx, shot.id)
    await settle_run(ctx, shot)
    await shoots.close_inactive(ctx, start + timedelta(hours=1))
    record = await repo.find_shoot_record(ctx.store, membership.shoot_id, 1)
    assert record is not None
    return record


async def test_identical_inputs_repeat_receipt_and_analysis_change_updates_provenance():
    first = await _settled_record_for_analysis(0.5)
    replay = await _settled_record_for_analysis(0.5)
    changed = await _settled_record_for_analysis(0.52)

    assert first.receipt == replay.receipt
    assert first.provenance.model_dump(exclude={"computed_at"}) == replay.provenance.model_dump(
        exclude={"computed_at"}
    )
    assert first.receipt == changed.receipt
    assert first.provenance.analysis_versions != changed.provenance.analysis_versions
