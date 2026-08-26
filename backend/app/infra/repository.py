"""Typed persistence on top of Store.

One function per read or write the services need, pydantic in and out. The
collection names and document ids are decided here and nowhere else.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel

from app.domain import run as run_rules
from app.domain import technique_map
from app.domain.entities import (
    ActivityEvent,
    Analysis,
    Experiment,
    ExperimentStatus,
    JourneyUpdate,
    Run,
    RunStage,
    RunStatus,
    RunStepState,
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
JOURNEY = "journey"
PAIRING = "pairing_codes"
DEVICES = "devices"


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
        stage=(
            "run_completed" if run.status is RunStatus.COMPLETED else "run_terminal"
        ),
        detail={
            "status": run.status.value,
            "source": run.source.value,
            "external_write": external_write,
            "stages": {
                stage: step.state.value for stage, step in run.steps.items()
            },
        },
        shot_id=run.shot_id,
        experiment_id=run.experiment_id,
        at=run.completed_at or run.updated_at,
    )
    await store.put(EVENTS, event.id, _dump(event))
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


async def put_device(store: Store, fingerprint: str, user_id: str, label: str) -> None:
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
        },
    )


async def find_device(store: Store, fingerprint: str) -> dict[str, Any] | None:
    return await store.get(DEVICES, fingerprint)
