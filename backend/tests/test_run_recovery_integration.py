"""Durable retry repair through the real Store, bus, blobs, and Ingest stage."""

from datetime import timedelta

from app.config import settings
from app.domain.entities import (
    Experiment,
    ExperimentStatus,
    ExperimentType,
    RunStage,
    RunStepState,
    Shot,
    ShotKind,
    ShotSource,
    ShotStatus,
    User,
    now,
)
from app.infra import repository as repo
from app.infra.bus import TOPICS, InProcessBus
from app.infra.storage import ORIGINAL, LocalBlobStore, blob_path
from app.infra.store import InMemoryStore
from app.services import ingest, recovery, runs
from app.services.context import Context
from tests.fixtures import jpeg_with_exif


async def test_scheduler_replays_a_stale_retry_through_real_ingest(tmp_path, monkeypatch):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    ctx.bus.subscribe(TOPICS["media.new"], lambda message: ingest.ingest(ctx, message))
    user = User(id="repair_user", email="repair@example.test")
    data = jpeg_with_exif(width=640, height=480)
    original = await ctx.blobs.write(
        blob_path(user.id, "repair_shot", ORIGINAL, "jpg"),
        data,
        "image/jpeg",
    )
    shot = Shot(
        id="repair_shot",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        source=ShotSource.WEB_UPLOAD,
        source_id="repair-source",
        filename="repair.jpg",
        mime_type="image/jpeg",
        status=ShotStatus.NEW,
        blobs={ORIGINAL: original},
    )
    await repo.put_user(ctx.store, user)
    await repo.put_shot(ctx.store, shot)
    run = await runs.ensure(ctx, shot)
    await repo.advance_run(
        ctx.store,
        run.id,
        RunStage.INGEST,
        RunStepState.RETRYING,
        "Temporary storage failure",
        {"error": "transient"},
        at=now() - timedelta(hours=1),
    )
    monkeypatch.setattr(settings, "run_repair_after_minutes", 15)

    repaired = await recovery.repair_retrying(ctx)
    await ctx.bus.drain()

    assert repaired == 1
    stored = await repo.get_shot(ctx.store, shot.id)
    assert stored.status is ShotStatus.INGESTED
    events = await repo.list_events(ctx.store, user.id)
    assert any(event.stage == "repair_replayed" for event in events)


async def test_scheduler_respects_active_analyst_lease(tmp_path, monkeypatch):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user = User(id="lease_user", email="lease@example.test")
    shot = Shot(
        id="lease_shot",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        source=ShotSource.WEB_UPLOAD,
        source_id="lease-source",
        filename="lease.jpg",
        mime_type="image/jpeg",
        status=ShotStatus.ANALYSING,
        analysing_at=now(),
    )
    await repo.put_user(ctx.store, user)
    await repo.put_shot(ctx.store, shot)
    run = await runs.ensure(ctx, shot)
    await repo.advance_run(
        ctx.store,
        run.id,
        RunStage.ANALYST,
        RunStepState.RETRYING,
        "Panel is retrying",
        at=now() - timedelta(hours=1),
    )
    monkeypatch.setattr(settings, "run_repair_after_minutes", 15)

    assert await recovery.repair_retrying(ctx) == 0
    assert not await repo.list_events(ctx.store, user.id)


async def test_scheduler_replays_closed_experiment_scout_event(tmp_path, monkeypatch):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    delivered: list[dict] = []

    async def receive(message: dict) -> None:
        delivered.append(message)

    ctx.bus.subscribe(TOPICS["experiment.closed"], receive)
    user = User(id="scout_repair_user", email="scout-repair@example.test")
    experiment = Experiment(
        id="closed_experiment",
        user_id=user.id,
        type=ExperimentType.REPRODUCE,
        title="Repeat the light",
        brief="Repeat the light from a previous Keeper",
        why_now="The record supports a deliberate retry",
        direction="Try the same light again",
        technique_id="backlighting",
        status=ExperimentStatus.COMPLETED,
    )
    shot = Shot(
        id="scout_repair_shot",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        source=ShotSource.WEB_UPLOAD,
        source_id="scout-repair-source",
        filename="scout-repair.jpg",
        mime_type="image/jpeg",
        status=ShotStatus.ANALYZED,
        experiment_id=experiment.id,
    )
    await repo.put_user(ctx.store, user)
    await repo.put_experiment(ctx.store, experiment)
    await repo.put_shot(ctx.store, shot)
    run = await runs.ensure(ctx, shot)
    await repo.advance_run(
        ctx.store,
        run.id,
        RunStage.SCOUT,
        RunStepState.RETRYING,
        "Scout failed after Experiment closure",
        at=now() - timedelta(hours=1),
    )
    monkeypatch.setattr(settings, "run_repair_after_minutes", 15)

    assert await recovery.repair_retrying(ctx) == 1
    await ctx.bus.drain()

    assert delivered == [
        {
            "user_id": user.id,
            "experiment_id": experiment.id,
            "shot_id": shot.id,
        }
    ]
