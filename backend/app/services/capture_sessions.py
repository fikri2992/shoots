"""Batch barriers for explicit system-camera Capture Sessions."""

from app.domain.entities import (
    CaptureMemberOutcome,
    CaptureSessionStatus,
    RunStatus,
    Verdict,
    now,
)
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.services import notify
from app.services.context import Context


async def expire_reserved(ctx: Context, user_id: str) -> int:
    """Expire abandoned reservations; committed manifests are never guessed away."""
    expired = 0
    at = now()
    for session in await repo.list_capture_sessions(ctx.store, user_id, limit=100):
        if session.status is not CaptureSessionStatus.RESERVED or session.expires_at > at:
            continue
        try:
            updated, changed = await repo.cancel_capture_session(
                ctx.store, session.id, at, expired=True
            )
        except repo.UnknownEntity:
            continue
        if not changed:
            continue
        await repo.release_capture_session_claim(ctx.store, updated.experiment_id, updated.id)
        await repo.record(
            ctx.store,
            updated.user_id,
            "scheduler",
            "capture_session_expired",
            {},
            experiment_id=updated.experiment_id,
        )
        expired += 1
    return expired


async def record_judge_outcome(
    ctx: Context,
    session_id: str,
    shot_id: str,
    verdict: Verdict | None,
    *,
    abstained: bool = False,
    terminal: bool = False,
) -> None:
    """Record one member and evaluate only when the whole batch has answered."""
    session = await repo.get_capture_session(ctx.store, session_id)
    if terminal:
        outcome = CaptureMemberOutcome.TERMINAL
    elif abstained:
        outcome = CaptureMemberOutcome.ABSTAINED
    elif verdict is not None and verdict.criteria_met:
        outcome = CaptureMemberOutcome.CRITERIA_MET
    else:
        outcome = CaptureMemberOutcome.CRITERIA_NOT_MET

    await repo.record_reproduce_batch_result(ctx.store, session.experiment_id, shot_id, verdict)
    session = await repo.record_capture_session_outcome(ctx.store, session.id, shot_id, outcome)
    if session.evaluated_at is not None or any(
        member.outcome is CaptureMemberOutcome.PENDING for member in session.members
    ):
        return

    ordered_members = sorted(session.members, key=lambda member: member.order)
    ordered_shot_ids = [member.shot_id for member in ordered_members if member.shot_id]
    experiment = await repo.get_experiment(ctx.store, session.experiment_id)
    verdict_by_shot = {item.shot_id: item for item in experiment.verdicts}
    met = [
        member.shot_id
        for member in ordered_members
        if member.shot_id
        and member.shot_id in verdict_by_shot
        and verdict_by_shot[member.shot_id].criteria_met
    ]
    judged = [
        member.shot_id
        for member in ordered_members
        if member.shot_id and member.outcome is not CaptureMemberOutcome.TERMINAL
    ]
    representative = met[0] if met else (judged[-1] if judged else "")
    at = now()
    experiment, completed_now = await repo.finalize_reproduce_batch(
        ctx.store,
        session.experiment_id,
        ordered_shot_ids,
        bool(met),
        at,
    )
    await repo.mark_capture_session_evaluated(ctx.store, session.id, representative, at)
    await repo.record(
        ctx.store,
        session.user_id,
        "judge",
        "capture_session_evaluated",
        {
            "members": len(session.members),
            "criteria_met": len(met),
            "representative_shot_id": representative,
        },
        experiment_id=session.experiment_id,
    )
    if completed_now:
        await repo.release_open_experiment(ctx.store, session.user_id, experiment.id)
        await ctx.bus.publish(
            TOPICS["experiment.closed"],
            {
                "user_id": session.user_id,
                "experiment_id": experiment.id,
                "shot_id": representative,
            },
        )


async def on_run_settled(ctx: Context, session_id: str, shot_id: str) -> None:
    """Close the Capture Session only after every member Run has settled."""
    session = await repo.get_capture_session(ctx.store, session_id)
    if session.status is CaptureSessionStatus.SETTLED:
        return
    run = await repo.find_run_for_shot(ctx.store, shot_id)
    if run is not None and run.status is RunStatus.TERMINAL:
        member = next((item for item in session.members if item.shot_id == shot_id), None)
        if member is not None and member.outcome is CaptureMemberOutcome.PENDING:
            await record_judge_outcome(
                ctx,
                session.id,
                shot_id,
                None,
                terminal=True,
            )
            session = await repo.get_capture_session(ctx.store, session_id)

    if session.evaluated_at is None or any(not member.shot_id for member in session.members):
        return
    runs = [await repo.find_run_for_shot(ctx.store, member.shot_id) for member in session.members]
    if any(
        member_run is None or member_run.status not in {RunStatus.COMPLETED, RunStatus.TERMINAL}
        for member_run in runs
    ):
        return

    summary = {
        "members": len(session.members),
        "completed": sum(
            member_run.status is RunStatus.COMPLETED for member_run in runs if member_run
        ),
        "terminal": sum(
            member_run.status is RunStatus.TERMINAL for member_run in runs if member_run
        ),
        "criteria_met": sum(
            member.outcome is CaptureMemberOutcome.CRITERIA_MET for member in session.members
        ),
        "criteria_not_met": sum(
            member.outcome is CaptureMemberOutcome.CRITERIA_NOT_MET for member in session.members
        ),
        "abstained": sum(
            member.outcome is CaptureMemberOutcome.ABSTAINED for member in session.members
        ),
    }
    settled, settled_now = await repo.settle_capture_session(ctx.store, session.id, summary, now())
    if not settled_now:
        return
    await repo.release_capture_session_claim(ctx.store, settled.experiment_id, settled.id)
    await repo.record(
        ctx.store,
        settled.user_id,
        "pipeline",
        "capture_session_settled",
        summary,
        experiment_id=settled.experiment_id,
    )
    await notify.capture_session_settled(ctx, settled)
    await repo.mark_capture_session_notification_attempted(ctx.store, settled.id, now())
