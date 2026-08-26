"""Durable Run accounting shared by every pipeline transport."""

from typing import Any

from app.domain.entities import Run, RunStage, RunStatus, RunStepState, Shot
from app.infra import repository as repo
from app.services.context import Context


async def ensure(ctx: Context, shot: Shot) -> Run:
    return await repo.ensure_run_for_shot(ctx.store, shot)


async def settle(
    ctx: Context,
    shot_id: str,
    stage: RunStage,
    state: RunStepState,
    outcome: str,
    detail: dict[str, Any] | None = None,
) -> Run:
    shot = await repo.get_shot(ctx.store, shot_id)
    run = await repo.find_run_for_shot(ctx.store, shot.id)
    if run is None:
        run = await ensure(ctx, shot)
    run, _ = await repo.advance_run(
        ctx.store,
        run.id,
        stage,
        state,
        outcome,
        detail,
    )
    if run.status in {RunStatus.COMPLETED, RunStatus.TERMINAL}:
        await repo.record_run_settled(ctx.store, run)
        if run.capture_session_id:
            from app.services import capture_sessions

            await capture_sessions.on_run_settled(ctx, run.capture_session_id, run.shot_id)
        from app.services import shoots

        await shoots.on_run_settled(ctx, run.shot_id)
    return run


async def completed(
    ctx: Context,
    shot_id: str,
    stage: RunStage,
    outcome: str,
    detail: dict[str, Any] | None = None,
) -> Run:
    return await settle(ctx, shot_id, stage, RunStepState.COMPLETED, outcome, detail)


async def skipped(
    ctx: Context,
    shot_id: str,
    stage: RunStage,
    outcome: str,
    detail: dict[str, Any] | None = None,
) -> Run:
    return await settle(ctx, shot_id, stage, RunStepState.SKIPPED, outcome, detail)


async def retrying(
    ctx: Context,
    shot_id: str,
    stage: RunStage,
    outcome: str,
    detail: dict[str, Any] | None = None,
) -> Run:
    return await settle(ctx, shot_id, stage, RunStepState.RETRYING, outcome, detail)


async def terminal(
    ctx: Context,
    shot_id: str,
    stage: RunStage,
    outcome: str,
    detail: dict[str, Any] | None = None,
) -> Run:
    return await settle(ctx, shot_id, stage, RunStepState.TERMINAL, outcome, detail)
