"""Typed persistence on top of Store.

One function per read or write the services need, pydantic in and out. The
collection names and document ids are decided here and nowhere else.
"""

import base64
import hashlib
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel

from app.domain import run as run_rules
from app.domain import technique_map
from app.domain.entities import (
    ActivityEvent,
    Analysis,
    CaptureMemberOutcome,
    CaptureSession,
    CaptureSessionMember,
    CaptureSessionStatus,
    Experiment,
    ExperimentStatus,
    JourneyUpdate,
    Run,
    RunStage,
    RunStatus,
    RunStepState,
    Scene,
    ScoutDecision,
    Shoot,
    ShootRecord,
    ShootStatus,
    Shot,
    ShotStatus,
    TechniqueState,
    User,
    Verdict,
    new_id,
    now,
)
from app.infra.store import Store

USERS = "users"
SHOTS = "shots"
ANALYSES = "analyses"
TECHNIQUE_STATES = "skills"  # legacy Firestore collection key; decision 62
EXPERIMENTS = "experiments"
OPEN_EXPERIMENTS = "open_experiments"
EVENTS = "events"
RUNS = "runs"
SCENES = "scenes"
SHOOTS = "shoots"
SHOOT_RECORDS = "shoot_records"
JOURNEY = "journey"
PAIRING = "pairing_codes"
DEVICES = "devices"
CAPTURE_SESSIONS = "capture_sessions"
ACTIVE_CAPTURE_SESSIONS = "active_capture_sessions"
ACCOUNT_DELETIONS = "account_deletions"


class UnknownEntity(LookupError):
    pass


def _dump(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


# --- users ----------------------------------------------------------------


async def put_user(store: Store, user: User) -> None:
    await store.put(USERS, user.id, _dump(user))


async def get_user(store: Store, user_id: str) -> User:
    data = await store.get(USERS, user_id)
    if data is None:
        raise UnknownEntity(f"user {user_id}")
    return User.model_validate(data)


async def find_user(store: Store, user_id: str) -> User | None:
    data = await store.get(USERS, user_id)
    return User.model_validate(data) if data else None


async def list_users(store: Store) -> list[User]:
    return [User.model_validate(d) for d in await store.query(USERS)]


# --- shots ----------------------------------------------------------------


def shot_id_for(user_id: str, drive_file_id: str) -> str:
    """Deterministic: the same Drive file can never become two shots."""
    return f"shot_{user_id[-8:]}_{drive_file_id}"


def source_shot_id_for(user_id: str, source: str, source_id: str) -> str:
    """A filesystem-safe id for non-Drive source references.

    Android MediaStore references may contain volume names and separators that
    are valid in Firestore but not in LocalBlobStore paths. The digest keeps the
    original reference private while preserving idempotency.
    """
    digest = hashlib.sha256(f"{source}:{source_id}".encode()).hexdigest()[:24]
    return f"shot_{user_id[-8:]}_{source}_{digest}"


async def put_shot(store: Store, shot: Shot) -> None:
    await store.put(SHOTS, shot.id, _dump(shot))


async def get_shot(store: Store, shot_id: str) -> Shot:
    data = await store.get(SHOTS, shot_id)
    if data is None:
        raise UnknownEntity(f"shot {shot_id}")
    return Shot.model_validate(data)


async def find_shot(store: Store, shot_id: str) -> Shot | None:
    data = await store.get(SHOTS, shot_id)
    return Shot.model_validate(data) if data else None


async def list_shots(store: Store, user_id: str, limit: int | None = None) -> list[Shot]:
    rows = await store.query(
        SHOTS, where={"user_id": user_id}, order_by="ingested_at", descending=True, limit=limit
    )
    return [Shot.model_validate(d) for d in rows]


async def list_shots_page(
    store: Store,
    user_id: str,
    limit: int,
    cursor: str = "",
) -> tuple[list[Shot], str]:
    """A stable, opaque-enough cursor without changing the legacy list body."""
    start_after = _decode_shot_cursor(cursor) if cursor else None
    rows = await store.query(
        SHOTS,
        where={"user_id": user_id},
        order_by="ingested_at",
        then_by="id",
        descending=True,
        limit=limit + 1,
        start_after=start_after,
    )
    has_more = len(rows) > limit
    shots = [Shot.model_validate(row) for row in rows[:limit]]
    next_cursor = ""
    if has_more and shots:
        next_cursor = _encode_shot_cursor(shots[-1].ingested_at.isoformat(), shots[-1].id)
    return shots, next_cursor


def _encode_shot_cursor(at: str, shot_id: str) -> str:
    return base64.urlsafe_b64encode(f"{at}\0{shot_id}".encode()).decode().rstrip("=")


def _decode_shot_cursor(value: str) -> dict[str, str]:
    if len(value) > 160:
        raise ValueError("Shot cursor is invalid")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
        at, shot_id = decoded.split("\0", 1)
        datetime.fromisoformat(at)
        if not shot_id:
            raise ValueError
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Shot cursor is invalid") from exc
    return {"ingested_at": at, "id": shot_id}


# --- scenes and shoots ----------------------------------------------------


async def put_scene(store: Store, scene: Scene) -> None:
    await store.put(SCENES, scene.id, _dump(scene))


async def get_scene(store: Store, scene_id: str) -> Scene:
    data = await store.get(SCENES, scene_id)
    if data is None:
        raise UnknownEntity(f"scene {scene_id}")
    return Scene.model_validate(data)


async def list_scenes_for_shoot(store: Store, shoot_id: str) -> list[Scene]:
    scenes = [
        Scene.model_validate(row) for row in await store.query(SCENES, where={"shoot_id": shoot_id})
    ]
    return sorted(scenes, key=lambda item: (item.started_at is None, item.started_at, item.id))


async def find_scene_for_shot(store: Store, user_id: str, shot_id: str) -> Scene | None:
    rows = await store.query(SCENES, where={"ordered_shot_ids": shot_id})
    scenes = sorted(
        (Scene.model_validate(row) for row in rows),
        key=lambda item: (item.grouping_revision, item.id),
        reverse=True,
    )
    return next((scene for scene in scenes if scene.user_id == user_id), None)


async def put_shoot(store: Store, shoot: Shoot) -> None:
    await store.put(SHOOTS, shoot.id, _dump(shoot))


async def get_shoot(store: Store, shoot_id: str) -> Shoot:
    data = await store.get(SHOOTS, shoot_id)
    if data is None:
        raise UnknownEntity(f"shoot {shoot_id}")
    return Shoot.model_validate(data)


async def list_shoots(store: Store, user_id: str) -> list[Shoot]:
    shoots = [
        Shoot.model_validate(row) for row in await store.query(SHOOTS, where={"user_id": user_id})
    ]
    return sorted(shoots, key=lambda item: (item.started_at is None, item.started_at, item.id))


async def list_all_shoots(store: Store) -> list[Shoot]:
    return [Shoot.model_validate(row) for row in await store.query(SHOOTS)]


async def mark_shoot_closing(store: Store, shoot_id: str) -> tuple[Shoot, bool]:
    def close(data: dict[str, Any]) -> dict[str, Any] | None:
        shoot = Shoot.model_validate(data)
        if shoot.status is ShootStatus.CLOSING:
            return data
        if shoot.status is not ShootStatus.OPEN:
            return None
        shoot.status = ShootStatus.CLOSING
        return _dump(shoot)

    data, changed = await store.mutate(SHOOTS, shoot_id, close)
    if data is None:
        raise UnknownEntity(f"shoot {shoot_id}")
    return Shoot.model_validate(data), changed


def shoot_record_id(shoot_id: str, revision: int) -> str:
    return f"{shoot_id}__r{revision}"


async def put_shoot_record_once(store: Store, record: ShootRecord) -> ShootRecord:
    record_id = shoot_record_id(record.shoot_id, record.revision)
    if await store.create(SHOOT_RECORDS, record_id, _dump(record)):
        return record
    data = await store.get(SHOOT_RECORDS, record_id)
    if data is None:
        raise UnknownEntity(f"Shoot Record {record_id}")
    return ShootRecord.model_validate(data)


async def find_shoot_record(store: Store, shoot_id: str, revision: int) -> ShootRecord | None:
    data = await store.get(SHOOT_RECORDS, shoot_record_id(shoot_id, revision))
    return ShootRecord.model_validate(data) if data else None


async def settle_shoot(
    store: Store, shoot_id: str, revision: int, settled_at: datetime
) -> tuple[Shoot, bool]:
    def settle(data: dict[str, Any]) -> dict[str, Any] | None:
        shoot = Shoot.model_validate(data)
        if shoot.revision != revision:
            return None
        if shoot.status is ShootStatus.SETTLED and shoot.current_record_revision == revision:
            return data
        if shoot.status is not ShootStatus.CLOSING:
            return None
        shoot.status = ShootStatus.SETTLED
        shoot.current_record_revision = revision
        shoot.closed_at = settled_at
        return _dump(shoot)

    data, changed = await store.mutate(SHOOTS, shoot_id, settle)
    if data is None:
        raise UnknownEntity(f"shoot {shoot_id}")
    return Shoot.model_validate(data), changed


# --- runs -----------------------------------------------------------------


async def ensure_run_for_shot(store: Store, shot: Shot) -> Run:
    """Create the Shot's deterministic Run before the first pipeline publish."""
    candidate = run_rules.for_shot(shot)
    if await store.create(RUNS, candidate.id, _dump(candidate)):
        return candidate
    data = await store.get(RUNS, candidate.id)
    if data is None:
        raise UnknownEntity(f"run {candidate.id}")
    return Run.model_validate(data)


async def get_run(store: Store, run_id: str) -> Run:
    data = await store.get(RUNS, run_id)
    if data is None:
        raise UnknownEntity(f"run {run_id}")
    return Run.model_validate(data)


async def find_run_for_shot(store: Store, shot_id: str) -> Run | None:
    data = await store.get(RUNS, f"run_{shot_id}")
    return Run.model_validate(data) if data else None


async def list_runs(store: Store, user_id: str, limit: int = 20) -> list[Run]:
    rows = await store.query(
        RUNS, where={"user_id": user_id}, order_by="started_at", descending=True, limit=limit
    )
    return [Run.model_validate(row) for row in rows]


async def advance_run(
    store: Store,
    run_id: str,
    stage: RunStage,
    state: RunStepState,
    outcome: str,
    detail: dict[str, Any] | None = None,
    at: datetime | None = None,
) -> tuple[Run, bool]:
    def advance(data: dict[str, Any]) -> dict[str, Any] | None:
        current = Run.model_validate(data)
        updated = run_rules.advance(current, stage, state, outcome, detail, at)
        if updated == current:
            return None
        return _dump(updated)

    data, changed = await store.mutate(RUNS, run_id, advance)
    if data is None:
        raise UnknownEntity(f"run {run_id}")
    return Run.model_validate(data), changed


async def claim_shot_for_ingest(
    store: Store, shot_id: str, claimed_at: datetime, stale_before: datetime
) -> tuple[Shot, bool]:
    """Atomically own one NEW or abandoned INGESTING Shot."""

    def claim(document: dict[str, Any]) -> dict[str, Any] | None:
        shot = Shot.model_validate(document)
        stale = shot.status is ShotStatus.INGESTING and (
            shot.ingesting_at is None or shot.ingesting_at < stale_before
        )
        if shot.status is not ShotStatus.NEW and not stale:
            return None
        shot.status = ShotStatus.INGESTING
        shot.ingesting_at = claimed_at
        return _dump(shot)

    data, changed = await store.mutate(SHOTS, shot_id, claim)
    if data is None:
        raise UnknownEntity(f"shot {shot_id}")
    return Shot.model_validate(data), changed


# --- analyses -------------------------------------------------------------


async def put_analysis(store: Store, analysis: Analysis) -> None:
    await store.put(ANALYSES, analysis.shot_id, _dump(analysis))


async def find_analysis(store: Store, shot_id: str) -> Analysis | None:
    data = await store.get(ANALYSES, shot_id)
    return Analysis.model_validate(data) if data else None


async def list_analyses(store: Store, user_id: str) -> list[Analysis]:
    rows = await store.query(ANALYSES, where={"user_id": user_id})
    return [Analysis.model_validate(row) for row in rows]


# --- technique states -----------------------------------------------------


def technique_state_id_for(user_id: str, technique_id: str) -> str:
    return f"{user_id}__{technique_id}"


async def put_technique_state(store: Store, state: TechniqueState) -> None:
    state = technique_map.normalise_state(state)
    await store.put(
        TECHNIQUE_STATES,
        technique_state_id_for(state.user_id, state.technique_id),
        _dump(state),
    )


async def list_technique_states(store: Store, user_id: str) -> list[TechniqueState]:
    rows = await store.query(TECHNIQUE_STATES, where={"user_id": user_id})
    return [technique_map.normalise_state(TechniqueState.model_validate(d)) for d in rows]


# --- experiments ---------------------------------------------------------------


async def put_experiment(store: Store, experiment: Experiment) -> None:
    await store.put(EXPERIMENTS, experiment.id, _dump(experiment))


async def append_verdict_if_open(
    store: Store,
    experiment_id: str,
    verdict: Verdict,
    closed_at: datetime,
) -> tuple[Experiment, bool]:
    """Compatibility wrapper for records created before result Shot sets."""
    return await record_reproduce_result_if_open(
        store, experiment_id, verdict.shot_id, verdict, closed_at
    )


async def record_reproduce_result_if_open(
    store: Store,
    experiment_id: str,
    shot_id: str,
    verdict: Verdict | None,
    closed_at: datetime,
) -> tuple[Experiment, bool]:
    """Record one explicit result and optional Verdict in one transaction.

    Abstention supplies ``verdict=None``. The result Shot still belongs in the
    Experiment Record, but the Experiment stays open.
    """

    def append(data: dict[str, Any]) -> dict[str, Any] | None:
        experiment = Experiment.model_validate(data)
        if experiment.status is not ExperimentStatus.OPEN:
            return None
        if shot_id in experiment.result_shot_ids:
            return None
        experiment.result_shot_ids.append(shot_id)
        if verdict is not None:
            experiment.verdicts.append(verdict)
        if verdict is not None and verdict.criteria_met:
            experiment.status = ExperimentStatus.COMPLETED
            experiment.closed_at = closed_at
        return _dump(experiment)

    data, changed = await store.mutate(EXPERIMENTS, experiment_id, append)
    if data is None:
        raise UnknownEntity(f"experiment {experiment_id}")
    return Experiment.model_validate(data), changed


async def transition_open_experiment(
    store: Store,
    experiment_id: str,
    status: ExperimentStatus,
    closed_at: datetime,
) -> tuple[Experiment, bool]:
    """Move one open Experiment to a terminal status without stale overwrites."""
    if status is ExperimentStatus.OPEN:
        raise ValueError("terminal Experiment status required")

    def transition(data: dict[str, Any]) -> dict[str, Any] | None:
        experiment = Experiment.model_validate(data)
        if experiment.status is not ExperimentStatus.OPEN:
            return None
        experiment.status = status
        experiment.closed_at = closed_at
        return _dump(experiment)

    data, changed = await store.mutate(EXPERIMENTS, experiment_id, transition)
    if data is None:
        raise UnknownEntity(f"experiment {experiment_id}")
    return Experiment.model_validate(data), changed


async def mark_experiment_delivered_if_open(
    store: Store, experiment_id: str, delivered_at: datetime
) -> bool:
    return await store.patch_if(
        EXPERIMENTS,
        experiment_id,
        {"delivered_at": delivered_at.isoformat()},
        {"status": ExperimentStatus.OPEN.value, "delivered_at": None},
    )


OPEN_SLOT_LEASE = timedelta(minutes=5)


async def create_open_experiment(store: Store, experiment: Experiment) -> bool:
    """Create the user's one-open claim and Experiment Record atomically."""
    if experiment.status is not ExperimentStatus.OPEN:
        raise ValueError("only an open Experiment may claim the open slot")
    slot = {
        "user_id": experiment.user_id,
        "experiment_id": experiment.id,
        "reserved_at": now().isoformat(),
    }
    return await store.create_claimed(
        OPEN_EXPERIMENTS,
        experiment.user_id,
        slot,
        EXPERIMENTS,
        experiment.id,
        _dump(experiment),
    )


async def get_experiment(store: Store, experiment_id: str) -> Experiment:
    data = await store.get(EXPERIMENTS, experiment_id)
    if data is None:
        raise UnknownEntity(f"experiment {experiment_id}")
    return Experiment.model_validate(data)


async def find_experiment(store: Store, experiment_id: str) -> Experiment | None:
    data = await store.get(EXPERIMENTS, experiment_id)
    return Experiment.model_validate(data) if data else None


async def open_experiment(store: Store, user_id: str) -> Experiment | None:
    slot = await store.get(OPEN_EXPERIMENTS, user_id)
    if slot is not None:
        experiment_id = str(slot.get("experiment_id", ""))
        data = await store.get(EXPERIMENTS, experiment_id) if experiment_id else None
        if data is not None:
            experiment = Experiment.model_validate(data)
            if experiment.status is ExperimentStatus.OPEN:
                return experiment
            await store.delete_if(OPEN_EXPERIMENTS, user_id, {"experiment_id": experiment_id})
        elif not _slot_expired(slot):
            return None
        else:
            await store.delete_if(OPEN_EXPERIMENTS, user_id, {"experiment_id": experiment_id})

    # Adopt a pre-slot open Experiment written by an older release.
    rows = await store.query(
        EXPERIMENTS,
        where={"user_id": user_id, "status": ExperimentStatus.OPEN.value},
        order_by="issued_at",
        limit=1,
    )
    if not rows:
        return None
    legacy = Experiment.model_validate(rows[0])
    claimed = await store.create(
        OPEN_EXPERIMENTS,
        user_id,
        {
            "user_id": user_id,
            "experiment_id": legacy.id,
            "reserved_at": now().isoformat(),
        },
    )
    if claimed:
        return legacy
    current = await store.get(OPEN_EXPERIMENTS, user_id)
    current_id = str(current.get("experiment_id", "")) if current else ""
    current_data = await store.get(EXPERIMENTS, current_id) if current_id else None
    if current_data is None:
        return None
    experiment = Experiment.model_validate(current_data)
    return experiment if experiment.status is ExperimentStatus.OPEN else None


async def release_open_experiment(store: Store, user_id: str, experiment_id: str) -> bool:
    return await store.delete_if(OPEN_EXPERIMENTS, user_id, {"experiment_id": experiment_id})


# --- Capture Sessions ------------------------------------------------------


async def create_capture_session(store: Store, session: CaptureSession) -> bool:
    """Reserve one nonterminal Capture Session for an Experiment atomically."""
    if session.status is not CaptureSessionStatus.RESERVED:
        raise ValueError("only a reserved Capture Session may claim an Experiment")
    claim = {
        "capture_session_id": session.id,
        "user_id": session.user_id,
        "experiment_id": session.experiment_id,
        "expires_at": session.expires_at.isoformat(),
    }
    return await store.create_claimed(
        ACTIVE_CAPTURE_SESSIONS,
        session.experiment_id,
        claim,
        CAPTURE_SESSIONS,
        session.id,
        _dump(session),
    )


async def get_capture_session(store: Store, session_id: str) -> CaptureSession:
    data = await store.get(CAPTURE_SESSIONS, session_id)
    if data is None:
        raise UnknownEntity(f"Capture Session {session_id}")
    return CaptureSession.model_validate(data)


async def find_capture_session(store: Store, session_id: str) -> CaptureSession | None:
    data = await store.get(CAPTURE_SESSIONS, session_id)
    return CaptureSession.model_validate(data) if data else None


async def list_capture_sessions(
    store: Store, user_id: str, limit: int = 20
) -> list[CaptureSession]:
    rows = await store.query(
        CAPTURE_SESSIONS,
        where={"user_id": user_id},
        order_by="reserved_at",
        descending=True,
        limit=limit,
    )
    return [CaptureSession.model_validate(row) for row in rows]


async def active_capture_session(store: Store, experiment_id: str) -> CaptureSession | None:
    claim = await store.get(ACTIVE_CAPTURE_SESSIONS, experiment_id)
    session_id = str(claim.get("capture_session_id", "")) if claim else ""
    return await find_capture_session(store, session_id) if session_id else None


async def commit_capture_session(
    store: Store,
    session_id: str,
    members: list[CaptureSessionMember],
    committed_at: datetime,
) -> tuple[CaptureSession, bool]:
    """Freeze an ordered manifest once. An identical retry is a no-op."""

    def commit(data: dict[str, Any]) -> dict[str, Any] | None:
        session = CaptureSession.model_validate(data)
        if session.status is CaptureSessionStatus.RESERVED:
            session.members = members
            session.status = CaptureSessionStatus.COMMITTED
            session.committed_at = committed_at
            return _dump(session)
        if (
            session.status
            in {
                CaptureSessionStatus.COMMITTED,
                CaptureSessionStatus.PROCESSING,
                CaptureSessionStatus.SETTLED,
            }
            and session.members == members
        ):
            return None
        return None

    data, changed = await store.mutate(CAPTURE_SESSIONS, session_id, commit)
    if data is None:
        raise UnknownEntity(f"Capture Session {session_id}")
    session = CaptureSession.model_validate(data)
    if not changed and not (
        session.status
        in {
            CaptureSessionStatus.COMMITTED,
            CaptureSessionStatus.PROCESSING,
            CaptureSessionStatus.SETTLED,
        }
        and session.members == members
    ):
        raise UnknownEntity(f"Capture Session {session_id} manifest differs")
    return session, changed


async def accept_capture_session_member(
    store: Store, session_id: str, source_id: str, shot_id: str
) -> CaptureSession:
    """Attach the accepted Shot id without changing the frozen membership."""

    def accept(data: dict[str, Any]) -> dict[str, Any] | None:
        session = CaptureSession.model_validate(data)
        if session.status not in {
            CaptureSessionStatus.COMMITTED,
            CaptureSessionStatus.PROCESSING,
        }:
            return None
        member = next((item for item in session.members if item.source_id == source_id), None)
        if member is None:
            return None
        if member.shot_id and member.shot_id != shot_id:
            return None
        member.shot_id = shot_id
        session.status = CaptureSessionStatus.PROCESSING
        return _dump(session)

    data, changed = await store.mutate(CAPTURE_SESSIONS, session_id, accept)
    if data is None:
        raise UnknownEntity(f"Capture Session {session_id}")
    session = CaptureSession.model_validate(data)
    member = next((item for item in session.members if item.source_id == source_id), None)
    if not changed and (
        session.status not in {CaptureSessionStatus.COMMITTED, CaptureSessionStatus.PROCESSING}
        or member is None
        or member.shot_id != shot_id
    ):
        raise UnknownEntity(f"Capture Session {session_id} does not accept {source_id}")
    return session


async def record_capture_session_outcome(
    store: Store,
    session_id: str,
    shot_id: str,
    outcome: CaptureMemberOutcome,
) -> CaptureSession:
    """Set one member's Judge or terminal-media outcome exactly once."""

    def record_outcome(data: dict[str, Any]) -> dict[str, Any] | None:
        session = CaptureSession.model_validate(data)
        member = next((item for item in session.members if item.shot_id == shot_id), None)
        if member is None:
            return None
        if member.outcome is not CaptureMemberOutcome.PENDING:
            return data if member.outcome is outcome else None
        member.outcome = outcome
        session.status = CaptureSessionStatus.PROCESSING
        return _dump(session)

    data, changed = await store.mutate(CAPTURE_SESSIONS, session_id, record_outcome)
    if data is None:
        raise UnknownEntity(f"Capture Session {session_id}")
    session = CaptureSession.model_validate(data)
    member = next((item for item in session.members if item.shot_id == shot_id), None)
    if not changed and (member is None or member.outcome is not outcome):
        raise UnknownEntity(f"Capture Session {session_id} has a different outcome")
    return session


async def record_reproduce_batch_result(
    store: Store,
    experiment_id: str,
    shot_id: str,
    verdict: Verdict | None,
) -> Experiment:
    """Append a session result without allowing one member to close the batch."""

    def append(data: dict[str, Any]) -> dict[str, Any]:
        experiment = Experiment.model_validate(data)
        if shot_id not in experiment.result_shot_ids:
            experiment.result_shot_ids.append(shot_id)
        if verdict is not None and not any(item.shot_id == shot_id for item in experiment.verdicts):
            experiment.verdicts.append(verdict)
        return _dump(experiment)

    data, _ = await store.mutate(EXPERIMENTS, experiment_id, append)
    if data is None:
        raise UnknownEntity(f"experiment {experiment_id}")
    return Experiment.model_validate(data)


async def finalize_reproduce_batch(
    store: Store,
    experiment_id: str,
    ordered_shot_ids: list[str],
    complete: bool,
    closed_at: datetime,
) -> tuple[Experiment, bool]:
    """Order the batch results and optionally complete Reproduce once."""
    completed_now = False

    def finalize(data: dict[str, Any]) -> dict[str, Any]:
        nonlocal completed_now
        experiment = Experiment.model_validate(data)
        batch = set(ordered_shot_ids)
        prior = [shot_id for shot_id in experiment.result_shot_ids if shot_id not in batch]
        experiment.result_shot_ids = prior + ordered_shot_ids
        verdict_by_shot = {verdict.shot_id: verdict for verdict in experiment.verdicts}
        prior_verdicts = [
            verdict for verdict in experiment.verdicts if verdict.shot_id not in batch
        ]
        experiment.verdicts = prior_verdicts + [
            verdict_by_shot[shot_id] for shot_id in ordered_shot_ids if shot_id in verdict_by_shot
        ]
        if complete and experiment.status is ExperimentStatus.OPEN:
            experiment.status = ExperimentStatus.COMPLETED
            experiment.closed_at = closed_at
            completed_now = True
        return _dump(experiment)

    data, _ = await store.mutate(EXPERIMENTS, experiment_id, finalize)
    if data is None:
        raise UnknownEntity(f"experiment {experiment_id}")
    return Experiment.model_validate(data), completed_now


async def mark_capture_session_evaluated(
    store: Store,
    session_id: str,
    representative_shot_id: str,
    evaluated_at: datetime,
) -> CaptureSession:
    def evaluate(data: dict[str, Any]) -> dict[str, Any]:
        session = CaptureSession.model_validate(data)
        if session.evaluated_at is None:
            session.representative_result_shot_id = representative_shot_id
            session.evaluated_at = evaluated_at
        return _dump(session)

    data, _ = await store.mutate(CAPTURE_SESSIONS, session_id, evaluate)
    if data is None:
        raise UnknownEntity(f"Capture Session {session_id}")
    return CaptureSession.model_validate(data)


async def settle_capture_session(
    store: Store,
    session_id: str,
    summary: dict[str, int],
    settled_at: datetime,
) -> tuple[CaptureSession, bool]:
    settled_now = False

    def settle(data: dict[str, Any]) -> dict[str, Any] | None:
        nonlocal settled_now
        session = CaptureSession.model_validate(data)
        if session.status is CaptureSessionStatus.SETTLED:
            return data
        if session.status is not CaptureSessionStatus.PROCESSING or session.evaluated_at is None:
            return None
        session.status = CaptureSessionStatus.SETTLED
        session.summary = summary
        session.settled_at = settled_at
        settled_now = True
        return _dump(session)

    data, _ = await store.mutate(CAPTURE_SESSIONS, session_id, settle)
    if data is None:
        raise UnknownEntity(f"Capture Session {session_id}")
    return CaptureSession.model_validate(data), settled_now


async def mark_capture_session_notification_attempted(
    store: Store, session_id: str, attempted_at: datetime
) -> CaptureSession:
    def mark(data: dict[str, Any]) -> dict[str, Any]:
        session = CaptureSession.model_validate(data)
        if session.notification_sent_at is None:
            session.notification_sent_at = attempted_at
        return _dump(session)

    data, _ = await store.mutate(CAPTURE_SESSIONS, session_id, mark)
    if data is None:
        raise UnknownEntity(f"Capture Session {session_id}")
    return CaptureSession.model_validate(data)


async def cancel_capture_session(
    store: Store,
    session_id: str,
    at: datetime,
    *,
    expired: bool = False,
) -> tuple[CaptureSession, bool]:
    changed_now = False

    def cancel(data: dict[str, Any]) -> dict[str, Any] | None:
        nonlocal changed_now
        session = CaptureSession.model_validate(data)
        wanted = CaptureSessionStatus.EXPIRED if expired else CaptureSessionStatus.CANCELLED
        if session.status is wanted:
            return data
        if session.status is not CaptureSessionStatus.RESERVED or session.members:
            return None
        session.status = wanted
        session.settled_at = at
        changed_now = True
        return _dump(session)

    data, _ = await store.mutate(CAPTURE_SESSIONS, session_id, cancel)
    if data is None:
        raise UnknownEntity(f"Capture Session {session_id}")
    session = CaptureSession.model_validate(data)
    wanted = CaptureSessionStatus.EXPIRED if expired else CaptureSessionStatus.CANCELLED
    if not changed_now and session.status is not wanted:
        raise UnknownEntity(f"Capture Session {session_id} cannot be cancelled")
    return session, changed_now


async def release_capture_session_claim(store: Store, experiment_id: str, session_id: str) -> bool:
    return await store.delete_if(
        ACTIVE_CAPTURE_SESSIONS,
        experiment_id,
        {"capture_session_id": session_id},
    )


async def attach_reference_clip_if_open(store: Store, experiment_id: str, path: str) -> bool:
    """Optional Director write that cannot overwrite or revive a closed record."""
    return await store.patch_if(
        EXPERIMENTS,
        experiment_id,
        {"reference_clip": path},
        {"status": ExperimentStatus.OPEN.value},
    )


def _slot_expired(slot: dict[str, Any]) -> bool:
    raw = slot.get("reserved_at")
    if not isinstance(raw, str):
        return True
    try:
        reserved_at = datetime.fromisoformat(raw)
    except ValueError:
        return True
    if reserved_at.tzinfo is None:
        reserved_at = reserved_at.replace(tzinfo=now().tzinfo)
    return now() - reserved_at >= OPEN_SLOT_LEASE


async def list_experiments(
    store: Store, user_id: str, limit: int | None = None
) -> list[Experiment]:
    rows = await store.query(
        EXPERIMENTS, where={"user_id": user_id}, order_by="issued_at", descending=True, limit=limit
    )
    return [Experiment.model_validate(d) for d in rows]


# --- events ---------------------------------------------------------------


async def record(
    store: Store,
    user_id: str,
    agent: str,
    stage: str,
    detail: dict[str, Any] | None = None,
    shot_id: str = "",
    experiment_id: str = "",
) -> ActivityEvent:
    event = ActivityEvent(
        id=new_id("evt"),
        user_id=user_id,
        agent=agent,
        stage=stage,
        detail=detail or {},
        shot_id=shot_id,
        experiment_id=experiment_id,
    )
    await store.put(EVENTS, event.id, _dump(event))
    return event


async def record_run_settled(store: Store, run: Run) -> ActivityEvent:
    """Write one replay-safe terminal ActivityEvent for a Run."""
    external_write = bool(run.steps[RunStage.SCRIBE.value].detail.get("external_write"))
    event = ActivityEvent(
        id=f"evt_{run.id}_settled",
        user_id=run.user_id,
        agent="pipeline",
        stage=("run_completed" if run.status is RunStatus.COMPLETED else "run_terminal"),
        detail={
            "status": run.status.value,
            "source": run.source.value,
            "external_write": external_write,
            "stages": {stage: step.state.value for stage, step in run.steps.items()},
        },
        shot_id=run.shot_id,
        experiment_id=run.experiment_id,
        at=run.completed_at or run.updated_at,
    )
    await store.put(EVENTS, event.id, _dump(event))
    return event


async def record_shoot_settled(store: Store, shoot: Shoot, record: ShootRecord) -> ActivityEvent:
    """Write one replay-safe terminal ActivityEvent for a Shoot revision."""
    event = ActivityEvent(
        id=f"evt_{shoot.id}_r{record.revision}_settled",
        user_id=shoot.user_id,
        agent="pipeline",
        stage="shoot_settled",
        detail={
            "shoot_id": shoot.id,
            "revision": record.revision,
            "scenes": len(record.scene_ids),
            "shots": len(record.shot_ids),
            "terminal": len(record.unreadable_shot_ids),
        },
        at=record.settled_at,
    )
    await store.put(EVENTS, event.id, _dump(event))
    return event


async def record_scout_decision(
    store: Store,
    shoot: Shoot,
    decision: ScoutDecision,
) -> ActivityEvent:
    """Write one replay-safe Scout choice for a Shoot revision."""
    event = ActivityEvent(
        id=f"evt_{shoot.id}_r{shoot.revision}_scout",
        user_id=shoot.user_id,
        agent="scout",
        stage="shoot_decision",
        detail={
            "shoot_id": shoot.id,
            "revision": shoot.revision,
            "route": decision.route.value,
            "reason": decision.reason,
            "experiment_id": decision.experiment_id,
            "rejected_routes": [item.route.value for item in decision.rejected_routes],
            "policy_version": decision.policy_version,
        },
        experiment_id=decision.experiment_id,
        at=decision.decided_at,
    )
    await store.create(EVENTS, event.id, _dump(event))
    return event


async def list_events(store: Store, user_id: str, limit: int = 100) -> list[ActivityEvent]:
    rows = await store.query(
        EVENTS, where={"user_id": user_id}, order_by="at", descending=True, limit=limit
    )
    return [ActivityEvent.model_validate(d) for d in rows]


# --- journey updates -------------------------------------------------------


async def put_journey_update(store: Store, update: JourneyUpdate) -> None:
    await store.put(JOURNEY, update.id, _dump(update))


async def list_journey_updates(store: Store, user_id: str, limit: int = 20) -> list[JourneyUpdate]:
    """Newest first: the photographer reads the current conclusion, and the
    older ones are the record of how it changed."""
    rows = await store.query(
        JOURNEY, where={"user_id": user_id}, order_by="created_at", descending=True, limit=limit
    )
    return [JourneyUpdate.model_validate(d) for d in rows]


async def latest_journey_update(store: Store, user_id: str) -> JourneyUpdate | None:
    found = await list_journey_updates(store, user_id, limit=1)
    return found[0] if found else None


# --- pairing a camera to an account ----------------------------------------


async def put_pairing_code(store: Store, code: str, user_id: str, expires_at: datetime) -> None:
    await store.put(
        PAIRING, code, {"code": code, "user_id": user_id, "expires_at": expires_at.isoformat()}
    )


async def spend_pairing_code(store: Store, code: str, at: datetime) -> str | None:
    """The user id the code stands for, and the code is gone either way.

    Single use is the point: a code read off a screen by someone else is worth
    one attempt within its window, not an open door. Deleting an expired code
    on the way past keeps the collection from growing without a sweeper.
    """
    data = await store.get(PAIRING, code)
    if data is None:
        return None
    await store.delete(PAIRING, code)
    if datetime.fromisoformat(data["expires_at"]) < at:
        return None
    return data["user_id"]


async def put_device(
    store: Store,
    fingerprint: str,
    user_id: str,
    label: str,
    *,
    expires_at: datetime | None = None,
    auth_method: str = "pairing",
) -> None:
    """Devices are keyed by the hash of their token: the store never holds a
    credential that would work if it leaked."""
    await store.put(
        DEVICES,
        fingerprint,
        {
            "fingerprint": fingerprint,
            "user_id": user_id,
            "label": label,
            "paired_at": now().isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "auth_method": auth_method,
            "notification_target": "",
        },
    )


async def find_device(store: Store, fingerprint: str) -> dict[str, Any] | None:
    return await store.get(DEVICES, fingerprint)


async def list_devices(store: Store, user_id: str) -> list[dict[str, Any]]:
    return await store.query(DEVICES, where={"user_id": user_id})


async def delete_device(store: Store, fingerprint: str) -> None:
    await store.delete(DEVICES, fingerprint)


async def set_device_notification_target(store: Store, fingerprint: str, target: str) -> bool:
    data, changed = await store.mutate(
        DEVICES,
        fingerprint,
        lambda current: {**current, "notification_target": target},
    )
    return data is not None and changed


# --- account deletion ------------------------------------------------------


async def request_account_deletion(store: Store, user_id: str) -> None:
    await store.put(
        ACCOUNT_DELETIONS,
        user_id,
        {
            "id": user_id,
            "user_id": user_id,
            "status": "requested",
            "requested_at": now().isoformat(),
        },
    )


async def delete_user_records(store: Store, user_id: str) -> None:
    """Delete every user-scoped document. External data is handled by the service."""
    collections: list[tuple[str, str | None]] = [
        (SHOTS, "id"),
        (ANALYSES, "shot_id"),
        (EXPERIMENTS, "id"),
        (EVENTS, "id"),
        (RUNS, "id"),
        (JOURNEY, "id"),
        (CAPTURE_SESSIONS, "id"),
        (DEVICES, "fingerprint"),
        (PAIRING, "code"),
        ("push", "id"),
    ]
    for collection, key in collections:
        for row in await store.query(collection, where={"user_id": user_id}):
            if key and row.get(key):
                await store.delete(collection, str(row[key]))
    for row in await store.query(TECHNIQUE_STATES, where={"user_id": user_id}):
        await store.delete(
            TECHNIQUE_STATES,
            technique_state_id_for(user_id, str(row.get("technique_id", ""))),
        )
    for row in await store.query(ACTIVE_CAPTURE_SESSIONS, where={"user_id": user_id}):
        if row.get("experiment_id"):
            await store.delete(ACTIVE_CAPTURE_SESSIONS, str(row["experiment_id"]))
    await store.delete(OPEN_EXPERIMENTS, user_id)
    await store.delete(USERS, user_id)
    await store.delete(ACCOUNT_DELETIONS, user_id)
