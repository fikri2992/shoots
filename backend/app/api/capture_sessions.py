"""Explicit system-camera batches for Reproduce Experiments."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from app.api.auth import current_user
from app.api.deps import get_context
from app.domain.entities import (
    CaptureSession,
    CaptureSessionMember,
    CaptureSessionStatus,
    ExperimentStatus,
    ExperimentType,
    Run,
    Shot,
    Verdict,
    new_id,
    now,
)
from app.infra import repository as repo
from app.services.context import Context

router = APIRouter(prefix="/api/capture-sessions", tags=["capture-sessions"])

SESSION_TTL = timedelta(hours=2)


class ReserveIn(BaseModel):
    experiment_id: str = Field(min_length=1, max_length=120)


class MemberIn(BaseModel):
    source_id: str = Field(min_length=1, max_length=300)
    order: int = Field(ge=0, le=999)


class ManifestIn(BaseModel):
    members: list[MemberIn] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_members(self) -> "ManifestIn":
        sources = [member.source_id for member in self.members]
        orders = [member.order for member in self.members]
        if len(sources) != len(set(sources)) or len(orders) != len(set(orders)):
            raise ValueError("Capture Session members and order values must be unique")
        return self


class CaptureSessionDetail(CaptureSession):
    shots: list[Shot] = Field(default_factory=list)
    runs: list[Run] = Field(default_factory=list)
    verdicts: list[Verdict] = Field(default_factory=list)


@router.post("", response_model=CaptureSession, status_code=status.HTTP_201_CREATED)
async def reserve(
    body: ReserveIn,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> CaptureSession:
    experiment = await repo.find_experiment(ctx.store, body.experiment_id)
    if experiment is None or experiment.user_id != session_user["id"]:
        raise HTTPException(404, "Experiment not found")
    if experiment.status is not ExperimentStatus.OPEN:
        raise HTTPException(409, "Experiment is not open")
    if experiment.type is not ExperimentType.REPRODUCE:
        raise HTTPException(409, "Capture Sessions currently require Reproduce")

    at = now()
    session = CaptureSession(
        id=new_id("capture"),
        user_id=experiment.user_id,
        experiment_id=experiment.id,
        device_id=str(session_user.get("device_id") or session_user.get("device") or "android"),
        device_label=str(session_user.get("device") or "Android")[:60],
        reserved_at=at,
        expires_at=at + SESSION_TTL,
    )
    if not await repo.create_capture_session(ctx.store, session):
        active = await repo.active_capture_session(ctx.store, experiment.id)
        if (
            active is not None
            and active.user_id == session.user_id
            and active.device_id == session.device_id
            and active.status is CaptureSessionStatus.RESERVED
            and active.expires_at > at
        ):
            return active
        if (
            active is not None
            and active.status is CaptureSessionStatus.RESERVED
            and active.expires_at <= at
        ):
            expired, changed = await repo.cancel_capture_session(
                ctx.store, active.id, at, expired=True
            )
            if changed:
                await repo.release_capture_session_claim(
                    ctx.store, expired.experiment_id, expired.id
                )
            if not await repo.create_capture_session(ctx.store, session):
                raise HTTPException(409, "This Experiment already has an active Capture Session")
        else:
            raise HTTPException(409, "This Experiment already has an active Capture Session")
    await repo.record(
        ctx.store,
        session.user_id,
        "phone_source",
        "capture_session_reserved",
        {"device": session.device_label},
        experiment_id=session.experiment_id,
    )
    return session


@router.put("/{session_id}/manifest", response_model=CaptureSession)
async def commit_manifest(
    session_id: str,
    body: ManifestIn,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> CaptureSession:
    session = await _owned(ctx, session_user["id"], session_id)
    if session.status is CaptureSessionStatus.RESERVED and session.expires_at <= now():
        raise HTTPException(409, "Capture Session expired before it was committed")
    members = [
        CaptureSessionMember(source_id=item.source_id, order=item.order)
        for item in sorted(body.members, key=lambda item: item.order)
    ]
    try:
        committed, changed = await repo.commit_capture_session(
            ctx.store, session.id, members, now()
        )
    except repo.UnknownEntity as exc:
        raise HTTPException(409, "Capture Session manifest is already different") from exc
    if changed:
        await repo.record(
            ctx.store,
            session.user_id,
            "phone_source",
            "capture_session_committed",
            {"members": len(members)},
            experiment_id=session.experiment_id,
        )
    return committed


@router.get("/{session_id}", response_model=CaptureSessionDetail)
async def get_session(
    session_id: str,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> CaptureSessionDetail:
    session = await _owned(ctx, session_user["id"], session_id)
    shots = []
    runs = []
    for member in sorted(session.members, key=lambda item: item.order):
        if not member.shot_id:
            continue
        shot = await repo.find_shot(ctx.store, member.shot_id)
        if shot is not None:
            shots.append(shot)
        run = await repo.find_run_for_shot(ctx.store, member.shot_id)
        if run is not None:
            runs.append(run)
    experiment = await repo.get_experiment(ctx.store, session.experiment_id)
    member_ids = {member.shot_id for member in session.members if member.shot_id}
    return CaptureSessionDetail(
        **session.model_dump(),
        shots=shots,
        runs=runs,
        verdicts=[item for item in experiment.verdicts if item.shot_id in member_ids],
    )


@router.post("/{session_id}/cancel", response_model=CaptureSession)
async def cancel(
    session_id: str,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> CaptureSession:
    session = await _owned(ctx, session_user["id"], session_id)
    try:
        cancelled, changed = await repo.cancel_capture_session(ctx.store, session.id, now())
    except repo.UnknownEntity as exc:
        raise HTTPException(409, "Only an empty reserved Capture Session can be cancelled") from exc
    if changed:
        await repo.release_capture_session_claim(ctx.store, session.experiment_id, session.id)
        await repo.record(
            ctx.store,
            session.user_id,
            "phone_source",
            "capture_session_cancelled",
            {},
            experiment_id=session.experiment_id,
        )
    return cancelled


async def _owned(ctx: Context, user_id: str, session_id: str) -> CaptureSession:
    session = await repo.find_capture_session(ctx.store, session_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(404, "Capture Session not found")
    return session
