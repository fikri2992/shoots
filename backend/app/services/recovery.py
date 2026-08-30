"""Scheduled liveness repair for Runs abandoned after bounded transport retries."""

from datetime import timedelta

from app.config import settings
from app.domain.entities import (
    ExperimentStatus,
    Run,
    RunStage,
    RunStatus,
    RunStepState,
    Shot,
    ShotStatus,
    now,
)
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.services.context import Context

_STAGE_ORDER = tuple(RunStage)
_TOPIC_BY_STAGE = {
    RunStage.INGEST: "media.new",
    RunStage.ANALYST: "media.ingested",
    RunStage.CARTOGRAPHER: "media.analyzed",
    RunStage.JUDGE: "media.analyzed",
    RunStage.SCRIBE: "media.judged",
}
_INGEST_LEASE_SECONDS = 600
_ANALYST_LEASE_SECONDS = 420


def _retrying_stage(run: Run) -> RunStage | None:
    return next(
        (
            stage
            for stage in _STAGE_ORDER
            if run.steps.get(stage.value) is not None
            and run.steps[stage.value].state is RunStepState.RETRYING
        ),
        None,
    )


def _lease_is_active(shot: Shot, stage: RunStage, at) -> bool:
    if stage is RunStage.INGEST and shot.status is ShotStatus.INGESTING:
        return bool(
            shot.ingesting_at and shot.ingesting_at > at - timedelta(seconds=_INGEST_LEASE_SECONDS)
        )
    if stage is RunStage.ANALYST and shot.status is ShotStatus.ANALYSING:
        return bool(
            shot.analysing_at and shot.analysing_at > at - timedelta(seconds=_ANALYST_LEASE_SECONDS)
        )
    return False


async def repair_retrying(ctx: Context) -> int:
    """Replay bounded stale Runs through their ordinary stage transport."""
    at = now()
    cutoff = at - timedelta(minutes=settings.run_repair_after_minutes)
    candidates: list[tuple[Run, Shot, RunStage]] = []
    for user in await repo.list_writable_users(ctx.store):
        for run in await repo.list_runs(ctx.store, user.id, limit=1000):
            if run.status is not RunStatus.RETRYING or run.updated_at > cutoff:
                continue
            stage = _retrying_stage(run)
            shot = await repo.find_shot(ctx.store, run.shot_id)
            if stage is None or shot is None or shot.superseded_at:
                continue
            if _lease_is_active(shot, stage, at):
                continue
            candidates.append((run, shot, stage))
    candidates.sort(key=lambda item: (item[0].updated_at, item[0].id))

    repaired = 0
    for run, shot, stage in candidates[: settings.run_repair_limit]:
        topic, message = await _repair_delivery(ctx, shot, stage)
        await ctx.bus.publish(TOPICS[topic], message)
        await repo.record(
            ctx.store,
            shot.user_id,
            "scheduler",
            "repair_replayed",
            {
                "run_id": run.id,
                "stage": stage.value,
                "retrying_since": run.updated_at.isoformat(),
            },
            shot_id=shot.id,
            experiment_id=shot.experiment_id,
        )
        repaired += 1
    return repaired


async def _repair_delivery(ctx: Context, shot: Shot, stage: RunStage) -> tuple[str, dict[str, str]]:
    """Return the original event shape that owns the retrying stage."""
    if stage is not RunStage.SCOUT:
        return _TOPIC_BY_STAGE[stage], {"shot_id": shot.id}
    experiment = (
        await repo.find_experiment(ctx.store, shot.experiment_id) if shot.experiment_id else None
    )
    if experiment is not None and experiment.status is ExperimentStatus.COMPLETED:
        return "experiment.closed", {
            "user_id": shot.user_id,
            "experiment_id": experiment.id,
            "shot_id": shot.id,
        }
    return "media.analyzed", {"shot_id": shot.id}
