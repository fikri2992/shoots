"""Scene and Shoot behaviour through the real module and Store seam."""

import asyncio
from datetime import UTC, datetime, timedelta

from app.domain.entities import Shot, ShotKind, ShotSource
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.store import InMemoryStore
from app.services import shoots
from app.services.context import Context


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
