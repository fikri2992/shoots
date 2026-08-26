"""Run accounting through the real service, repository, and Store."""

import asyncio

from app.api import deps
from app.domain.entities import (
    Analysis,
    RunStage,
    RunStatus,
    RunStepState,
    Shot,
    ShotKind,
    ShotStatus,
    User,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import runs
from app.services.context import Context


def context() -> Context:
    return Context(
        store=InMemoryStore(),
        blobs=None,
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )


async def accepted_shot(ctx: Context, shot_id: str = "shot_run") -> Shot:
    shot = Shot(
        id=shot_id,
        user_id="run_user",
        kind=ShotKind.PHOTO,
        filename="run.jpg",
        mime_type="image/jpeg",
    )
    await repo.put_shot(ctx.store, shot)
    await runs.ensure(ctx, shot)
    return shot


async def test_scribe_cannot_complete_a_run_before_cartographer_and_scout():
    ctx = context()
    shot = await accepted_shot(ctx)

    await asyncio.gather(
        runs.completed(ctx, shot.id, RunStage.SCRIBE, "No Drive output", {"external_write": False}),
        runs.completed(ctx, shot.id, RunStage.INGEST, "Measured"),
        runs.completed(ctx, shot.id, RunStage.ANALYST, "Read"),
        runs.completed(ctx, shot.id, RunStage.JUDGE, "Free Shot"),
    )
    before_map = await repo.find_run_for_shot(ctx.store, shot.id)
    assert before_map is not None
    assert before_map.status is RunStatus.RUNNING

    await runs.completed(ctx, shot.id, RunStage.CARTOGRAPHER, "Map checked")
    before_scout = await repo.find_run_for_shot(ctx.store, shot.id)
    assert before_scout is not None
    assert before_scout.status is RunStatus.RUNNING

    await runs.completed(ctx, shot.id, RunStage.SCOUT, "Stayed silent")
    finished = await repo.find_run_for_shot(ctx.store, shot.id)
    assert finished is not None
    assert finished.status is RunStatus.COMPLETED
    assert finished.completed_at is not None

    events = await repo.list_events(ctx.store, shot.user_id)
    assert [(event.agent, event.stage) for event in events] == [("pipeline", "run_completed")]


async def test_retry_and_terminal_media_are_distinct_run_results():
    ctx = context()
    retry_shot = await accepted_shot(ctx, "shot_retry")
    terminal_shot = await accepted_shot(ctx, "shot_terminal")

    await runs.retrying(ctx, retry_shot.id, RunStage.INGEST, "Network unavailable")
    retrying = await repo.find_run_for_shot(ctx.store, retry_shot.id)
    assert retrying is not None and retrying.status is RunStatus.RETRYING
    await runs.completed(ctx, retry_shot.id, RunStage.INGEST, "Measured on retry")
    resumed = await repo.find_run_for_shot(ctx.store, retry_shot.id)
    assert resumed is not None and resumed.status is RunStatus.RUNNING

    await runs.terminal(ctx, terminal_shot.id, RunStage.INGEST, "Unreadable bytes")
    terminal = await repo.find_run_for_shot(ctx.store, terminal_shot.id)
    assert terminal is not None and terminal.status is RunStatus.TERMINAL
    assert all(step.state is not RunStepState.PENDING for step in terminal.steps.values())
    events = await repo.list_events(ctx.store, terminal_shot.user_id)
    assert any(
        event.stage == "run_terminal" and event.shot_id == terminal_shot.id
        for event in events
    )


async def test_real_fanout_settles_only_after_map_scout_judge_and_scribe(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    await repo.put_user(ctx.store, User(id="run_user", email="run@example.com"))
    shot = await accepted_shot(ctx, "shot_fanout")
    shot.status = ShotStatus.ANALYZED
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(shot_id=shot.id, user_id=shot.user_id, model="stored-reader"),
    )
    await runs.completed(ctx, shot.id, RunStage.INGEST, "Measured")
    await runs.completed(ctx, shot.id, RunStage.ANALYST, "Read")
    deps.wire(ctx)

    await ctx.bus.publish("shoots.media.analyzed", {"shot_id": shot.id})
    await ctx.bus.drain()

    run = await repo.find_run_for_shot(ctx.store, shot.id)
    assert run is not None and run.status is RunStatus.COMPLETED
    assert all(
        step.state in {RunStepState.COMPLETED, RunStepState.SKIPPED}
        for step in run.steps.values()
    )
    events = await repo.list_events(ctx.store, shot.user_id)
    assert sum(event.stage == "run_completed" for event in events) == 1
    assert any(event.stage == "shoot_decision_deferred" for event in events)
