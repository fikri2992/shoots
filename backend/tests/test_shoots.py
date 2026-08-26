"""Scene and Shoot behaviour through the real module and Store seam."""

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.config import settings
from app.domain.entities import (
    CaptureSession,
    CaptureSessionMember,
    CaptureSessionStatus,
    RunStage,
    ShootStatus,
    Shot,
    ShotKind,
    ShotSource,
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
