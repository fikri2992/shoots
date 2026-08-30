"""Apply explicit Mine/Inspiration corrections without blending authorities."""

from app.domain.entities import (
    Inspiration,
    PhotographerSignal,
    PhotographerSignalKind,
    RunStatus,
    Shot,
    ShotKind,
    ShotStatus,
    SignalScope,
    SignalSource,
    now,
)
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.services import cartographer, ingest, photographer_memory, runs
from app.services.context import Context


class SourceRoleConflict(ValueError):
    pass


async def shot_to_inspiration(ctx: Context, user_id: str, shot_id: str) -> Inspiration:
    shot = await repo.find_shot(ctx.store, shot_id)
    if shot is None or shot.user_id != user_id:
        raise repo.UnknownEntity(f"Shot {shot_id}")
    if shot.superseded_by_inspiration_id:
        existing = await repo.find_inspiration(ctx.store, shot.superseded_by_inspiration_id)
        if existing is not None and not existing.superseded_at:
            return existing
    await _require_free(ctx, shot)
    inspiration_id = repo.source_inspiration_id_for(user_id, shot.source.value, shot.source_id)
    inspiration = await repo.find_inspiration(ctx.store, inspiration_id)
    if inspiration is None:
        inspiration = Inspiration(
            id=inspiration_id,
            user_id=user_id,
            source=shot.source,
            source_id=shot.source_id,
            filename=shot.filename,
            mime_type=shot.mime_type,
            blobs=dict(shot.blobs),
            source_shot_id=shot.id,
        )
        await repo.put_inspiration(ctx.store, inspiration)
    shot.superseded_at = now()
    shot.superseded_by_inspiration_id = inspiration.id
    await repo.put_shot(ctx.store, shot)
    await record_source_role(
        ctx,
        user_id,
        SignalScope.INSPIRATION,
        inspiration.id,
        "inspiration",
        related_scope_ids={shot.id, inspiration.id},
    )
    superseded_journey = await repo.supersede_journey_for_shot(
        ctx.store,
        user_id,
        shot.id,
        shot.superseded_at,
    )
    await cartographer.rebuild(ctx, user_id)
    await repo.record(
        ctx.store,
        user_id,
        "photographer",
        "source_role_corrected",
        {
            "from": "mine",
            "to": "inspiration",
            "inspiration_id": inspiration.id,
            "superseded_journey_updates": superseded_journey,
        },
        shot_id=shot.id,
    )
    return inspiration


async def inspiration_to_shot(ctx: Context, user_id: str, inspiration_id: str) -> Shot:
    inspiration = await repo.find_inspiration(ctx.store, inspiration_id)
    if inspiration is None or inspiration.user_id != user_id:
        raise repo.UnknownEntity(f"Inspiration {inspiration_id}")
    if inspiration.superseded_at and inspiration.restored_shot_id:
        restored = await repo.find_shot(ctx.store, inspiration.restored_shot_id)
        if restored is not None and not restored.superseded_by_inspiration_id:
            return restored

    shot = (
        await repo.find_shot(ctx.store, inspiration.source_shot_id)
        if inspiration.source_shot_id
        else None
    )
    created = shot is None
    if shot is None:
        shot = Shot(
            id=repo.source_shot_id_for(
                user_id,
                inspiration.source.value,
                inspiration.source_id,
            ),
            user_id=user_id,
            kind=_kind_for(inspiration.mime_type),
            source=inspiration.source,
            source_id=inspiration.source_id,
            filename=inspiration.filename,
            mime_type=inspiration.mime_type,
            blobs=dict(inspiration.blobs),
        )
    shot.superseded_at = None
    shot.superseded_by_inspiration_id = ""
    await repo.put_shot(ctx.store, shot)
    await record_source_role(
        ctx,
        user_id,
        SignalScope.SHOT,
        shot.id,
        "mine",
        related_scope_ids={shot.id, inspiration.id},
    )
    inspiration.superseded_at = now()
    inspiration.restored_shot_id = shot.id
    await repo.put_inspiration(ctx.store, inspiration)
    existing_run = await repo.find_run_for_shot(ctx.store, shot.id)
    if created or (existing_run is None and await repo.find_analysis(ctx.store, shot.id) is None):
        await runs.ensure(ctx, shot)
    await cartographer.rebuild(ctx, user_id)
    if created:
        await ctx.bus.publish(TOPICS["media.new"], {"shot_id": shot.id})
    else:
        if shot.status is not ShotStatus.ANALYZED:
            await ingest.resume(ctx, shot)
    await repo.record(
        ctx.store,
        user_id,
        "photographer",
        "source_role_corrected",
        {
            "from": "inspiration",
            "to": "mine",
            "inspiration_id": inspiration.id,
        },
        shot_id=shot.id,
    )
    return shot


async def _require_free(ctx: Context, shot: Shot) -> None:
    if shot.source.value == "android" and ":external:" in shot.source_id:
        raise SourceRoleConflict("Approved Camera media remains Mine by source contract")
    if shot.experiment_id or shot.capture_session_id:
        raise SourceRoleConflict("Experiment-bound Shots cannot yet become Inspiration")
    run = await repo.find_run_for_shot(ctx.store, shot.id)
    if run is not None and run.status not in {RunStatus.COMPLETED, RunStatus.TERMINAL}:
        raise SourceRoleConflict("Wait for this Shot's current Run to settle before correcting it")
    for experiment in await repo.list_experiments(ctx.store, shot.user_id):
        cited = (
            shot.id == experiment.reference_shot_id
            or shot.id in experiment.warrant_shot_ids
            or shot.id in experiment.result_shot_ids
        )
        if cited:
            raise SourceRoleConflict("A Shot cited by an Experiment cannot yet become Inspiration")


def _kind_for(mime_type: str) -> ShotKind:
    return ShotKind.VIDEO if mime_type.startswith("video/") else ShotKind.PHOTO


async def record_source_role(
    ctx: Context,
    user_id: str,
    scope: SignalScope,
    scope_id: str,
    value: str,
    *,
    related_scope_ids: set[str] | None = None,
) -> PhotographerSignal:
    related_scope_ids = related_scope_ids or {scope_id}
    current = next(
        (
            signal
            for signal in await repo.list_photographer_signals(ctx.store, user_id)
            if signal.scope_id in related_scope_ids
            and signal.kind is PhotographerSignalKind.SOURCE_ROLE
        ),
        None,
    )
    provenance = f"source-role:{current.id if current else 'initial'}:{value}"
    signal_id = photographer_memory.stable_signal_id(
        user_id,
        scope,
        scope_id,
        PhotographerSignalKind.SOURCE_ROLE,
        value,
        provenance,
    )
    return await photographer_memory.apply_photographer_signal(
        ctx,
        PhotographerSignal(
            id=signal_id,
            user_id=user_id,
            scope=scope,
            scope_id=scope_id,
            kind=PhotographerSignalKind.SOURCE_ROLE,
            value=value,
            source=SignalSource.PHOTOGRAPHER_ACTION,
            source_event_id=f"evt_{signal_id}_signal_stored",
            supersedes_signal_id=current.id if current else "",
        ),
    )
