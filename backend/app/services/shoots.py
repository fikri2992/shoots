"""Persist capture-continuous Scene and Shoot membership."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.config import settings
from app.domain import shoot_receipt
from app.domain import shoots as rules
from app.domain.entities import (
    Provenance,
    RunStatus,
    Scene,
    Shoot,
    ShootRecord,
    ShootStatus,
    new_id,
    now,
)
from app.infra import repository as repo
from app.services import profile as profile_service
from app.services import shoot_scout
from app.services.context import Context


@dataclass(frozen=True)
class ShootMembership:
    shoot_id: str
    scene_id: str
    shoot_revision: int


async def latest(ctx: Context, user_id: str) -> Shoot | None:
    """Newest natural Shoot for one Photographer."""
    items = await repo.list_shoots(ctx.store, user_id)
    return max(
        items,
        key=lambda item: (
            item.last_capture_at is not None,
            item.last_capture_at or item.started_at or datetime.min.replace(tzinfo=UTC),
            item.id,
        ),
        default=None,
    )


async def latest_record(ctx: Context, user_id: str) -> ShootRecord | None:
    """Newest immutable Shoot Record, including an earlier settled Shoot."""
    records = await repo.list_shoot_records(ctx.store, user_id, limit=1)
    return records[0] if records else None


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
    elif shoot.status is ShootStatus.SETTLED:
        shoot = await _start_revision(ctx, shoot)

    current_scenes = [
        item
        for item in await repo.list_scenes_for_shoot(ctx.store, shoot.id)
        if item.grouping_revision == shoot.revision
    ]
    scene = rules.choose_scene(current_scenes, at)
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
    scenes = [
        item
        for item in await repo.list_scenes_for_shoot(ctx.store, shoot.id)
        if item.grouping_revision == shoot.revision
    ]
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


async def _start_revision(ctx: Context, shoot: Shoot) -> Shoot:
    """Clone settled Scene membership before accepting late Camera media."""
    next_revision = shoot.revision + 1
    cloned_scene_ids: list[str] = []
    for scene in await repo.list_scenes_for_shoot(ctx.store, shoot.id):
        if scene.grouping_revision != shoot.revision:
            continue
        cloned = scene.model_copy(
            update={
                "id": new_id("scene"),
                "grouping_revision": next_revision,
            },
            deep=True,
        )
        await repo.put_scene(ctx.store, cloned)
        cloned_scene_ids.append(cloned.id)
    revised = shoot.model_copy(deep=True)
    revised.status = ShootStatus.CLOSING
    revised.revision = next_revision
    revised.current_record_revision = next_revision
    revised.ordered_scene_ids = cloned_scene_ids
    revised.closed_at = None
    await repo.put_shoot(ctx.store, revised)
    return revised


async def close_inactive(ctx: Context, at: datetime | None = None) -> list[str]:
    """Move inactive Shoots to closing and settle any whose Runs already ended."""
    at = at or now()
    cutoff = at - timedelta(minutes=settings.shoot_gap_minutes)
    changed: list[str] = []
    for shoot in await repo.list_all_shoots(ctx.store):
        if shoot.status is ShootStatus.CLOSING:
            await _settle_if_ready(ctx, shoot)
            continue
        if (
            shoot.status is not ShootStatus.OPEN
            or shoot.last_capture_at is None
            or shoot.last_capture_at > cutoff
        ):
            continue
        closing, closed_now = await repo.mark_shoot_closing(ctx.store, shoot.id)
        if closed_now:
            changed.append(closing.id)
        await _settle_if_ready(ctx, closing)
    return changed


async def on_run_settled(ctx: Context, shot_id: str) -> ShootRecord | None:
    """Settle the Shot's closing Shoot, or return its existing current record."""
    shot = await repo.get_shot(ctx.store, shot_id)
    scene = await repo.find_scene_for_shot(ctx.store, shot.user_id, shot.id)
    if scene is None:
        return None
    shoot = await repo.get_shoot(ctx.store, scene.shoot_id)
    if shoot.status is ShootStatus.OPEN:
        return None
    return await _settle_if_ready(ctx, shoot)


async def _settle_if_ready(ctx: Context, shoot: Shoot) -> ShootRecord | None:
    existing = await repo.find_shoot_record(ctx.store, shoot.id, shoot.revision)
    if shoot.status is ShootStatus.SETTLED:
        return existing
    if existing is not None:
        settled, changed = await repo.settle_shoot(
            ctx.store,
            shoot.id,
            shoot.revision,
            existing.settled_at,
        )
        if changed:
            await repo.record_shoot_settled(ctx.store, settled, existing)
        return existing

    runs = [await repo.find_run_for_shot(ctx.store, shot_id) for shot_id in shoot.ordered_shot_ids]
    if any(
        run is None or run.status not in {RunStatus.COMPLETED, RunStatus.TERMINAL} for run in runs
    ):
        return None

    run_outcomes = {run.shot_id: run.status.value for run in runs if run is not None}
    settled_at = max(
        (run.completed_at or run.updated_at for run in runs if run is not None),
        default=now(),
    )
    shots = [await repo.get_shot(ctx.store, shot_id) for shot_id in shoot.ordered_shot_ids]
    member_ids = set(shoot.ordered_shot_ids)
    analyses = [
        analysis
        for analysis in await repo.list_analyses(ctx.store, shoot.user_id)
        if analysis.shot_id in member_ids
    ]
    scenes = [await repo.get_scene(ctx.store, scene_id) for scene_id in shoot.ordered_scene_ids]
    current_profile = await profile_service.build_for_shots(
        ctx,
        shoot.user_id,
        set(shoot.ordered_shot_ids),
    )
    analyzed_shot_ids = {analysis.shot_id for analysis in analyses}
    unreadable_shot_ids = [
        run.shot_id
        for run in runs
        if run is not None
        and run.status is RunStatus.TERMINAL
        and run.shot_id not in analyzed_shot_ids
    ]
    receipt = shoot_receipt.synthesize(
        shot_ids=shoot.ordered_shot_ids,
        scene_shot_ids=[scene.ordered_shot_ids for scene in scenes],
        shots=shots,
        analyses=analyses,
        profile=current_profile,
        unreadable_shot_ids=unreadable_shot_ids,
    )
    base_provenance = profile_service.provenance(current_profile)
    provenance = Provenance(
        shot_ids=list(shoot.ordered_shot_ids),
        sample_size=len(shoot.ordered_shot_ids),
        calc_version=receipt.calc_version,
        inputs=base_provenance.inputs,
        analysis_versions=base_provenance.analysis_versions,
    )
    from app.services import cartographer

    await cartographer.rebuild(ctx, shoot.user_id)
    scout_decision = await shoot_scout.decide(ctx, shoot, receipt)
    record = await repo.put_shoot_record_once(
        ctx.store,
        ShootRecord(
            shoot_id=shoot.id,
            user_id=shoot.user_id,
            revision=shoot.revision,
            scene_ids=list(shoot.ordered_scene_ids),
            shot_ids=list(shoot.ordered_shot_ids),
            run_outcomes=run_outcomes,
            unreadable_shot_ids=unreadable_shot_ids,
            receipt=receipt,
            scout=scout_decision,
            provenance=provenance,
            settled_at=settled_at,
        ),
    )
    settled, changed = await repo.settle_shoot(ctx.store, shoot.id, shoot.revision, settled_at)
    if changed:
        await repo.record_shoot_settled(ctx.store, settled, record)
    return record


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
