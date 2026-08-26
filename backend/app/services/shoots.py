"""Persist capture-continuous Scene and Shoot membership."""

from dataclasses import dataclass
from datetime import timedelta

from app.config import settings
from app.domain import shoots as rules
from app.domain.entities import Scene, Shoot, new_id
from app.infra import repository as repo
from app.services.context import Context


@dataclass(frozen=True)
class ShootMembership:
    shoot_id: str
    scene_id: str
    shoot_revision: int


async def observe_shot(ctx: Context, shot_id: str) -> ShootMembership:
    """Assign one stored Shot exactly once using capture continuity."""
    shot = await repo.get_shot(ctx.store, shot_id)
    existing_scene = await repo.find_scene_for_shot(ctx.store, shot.user_id, shot.id)
    if existing_scene is not None:
        existing_shoot = await repo.get_shoot(ctx.store, existing_scene.shoot_id)
        return ShootMembership(existing_shoot.id, existing_scene.id, existing_shoot.revision)

    at = rules.capture_instant(shot)
    shoot = rules.choose_shoot(
        await repo.list_shoots(ctx.store, shot.user_id),
        at,
        timedelta(minutes=settings.shoot_gap_minutes),
    )
    if shoot is None:
        shoot = Shoot(
            id=new_id("shoot"),
            user_id=shot.user_id,
            device_id=rules.device_id(shot),
            started_at=at,
            last_capture_at=at,
        )

    scene = rules.choose_scene(await repo.list_scenes_for_shoot(ctx.store, shoot.id), at)
    if scene is None:
        scene = Scene(
            id=new_id("scene"),
            user_id=shot.user_id,
            shoot_id=shoot.id,
            started_at=at,
            ended_at=at,
        )

    rules.include_in_scene(scene, shot.id, at)
    rules.include_in_shoot(shoot, scene.id, shot.id, at)
    scene.ordered_shot_ids = await _ordered_shot_ids(ctx, scene.ordered_shot_ids)
    await repo.put_scene(ctx.store, scene)
    shoot.ordered_shot_ids = await _ordered_shot_ids(ctx, shoot.ordered_shot_ids)
    scenes = await repo.list_scenes_for_shoot(ctx.store, shoot.id)
    shoot.ordered_scene_ids = [
        item.id
        for item in sorted(
            scenes,
            key=lambda item: (
                item.started_at is None,
                item.started_at or item.ended_at,
                item.id,
            ),
        )
    ]
    await repo.put_shoot(ctx.store, shoot)
    return ShootMembership(shoot.id, scene.id, shoot.revision)


async def _ordered_shot_ids(ctx: Context, shot_ids: list[str]) -> list[str]:
    shots = [await repo.get_shot(ctx.store, shot_id) for shot_id in set(shot_ids)]
    return [
        shot.id
        for shot in sorted(
            shots,
            key=lambda item: (
                rules.capture_instant(item) is None,
                rules.capture_instant(item) or item.ingested_at,
                item.id,
            ),
        )
    ]
