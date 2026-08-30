"""Compact read model for the offline-capable Android client."""

import hashlib
import json

from fastapi import APIRouter, Depends, Header, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api import experiments as experiment_api
from app.api import shots as shot_api
from app.api.auth import current_user
from app.api.deps import get_context
from app.domain.entities import (
    CaptureSession,
    Deconstruction,
    Experiment,
    ExperimentDirection,
    Inspiration,
    InterventionRecord,
    JourneyUpdate,
    PhotographerSignal,
    Run,
    ScoutAnswer,
    Shoot,
    ShootRecord,
    Shot,
    User,
)
from app.infra import repository as repo
from app.services import shoots
from app.services.context import Context

router = APIRouter(prefix="/api/mobile", tags=["mobile"])


class MobileSnapshot(BaseModel):
    user: User
    drive_connected: bool
    drive_folder_url: str
    open_experiment: Experiment | None
    latest_capture_session: CaptureSession | None
    latest_run: Run | None
    latest_shoot: Shoot | None
    latest_shoot_record: ShootRecord | None
    latest_shot: shot_api.ShotView | None
    recent_shots: list[Shot]
    recent_inspirations: list[Inspiration]
    photographer_signals: list[PhotographerSignal]
    journey: list[JourneyUpdate]
    profile: shot_api.ProfileView
    techniques: list[experiment_api.TechniqueNode]
    technique_catalogue: list[experiment_api.TechniqueChoice]
    experiments: list[Experiment]
    experiment_directions: list[ExperimentDirection]
    latest_deconstruction: Deconstruction | None
    recent_scout_answers: list[ScoutAnswer]
    recent_interventions: list[InterventionRecord]


@router.get("/snapshot", response_model=MobileSnapshot)
async def snapshot(
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Response:
    user = await repo.get_user(ctx.store, session_user["id"])
    sessions = await repo.list_capture_sessions(ctx.store, user.id, limit=1)
    runs = await repo.list_runs(ctx.store, user.id, limit=1)
    experiments = await repo.list_experiments(ctx.store, user.id, limit=20)
    directions = await repo.list_experiment_directions(ctx.store, user.id, limit=50)
    deconstructions = await repo.list_deconstructions(ctx.store, user.id, limit=1)
    shots = await repo.list_shots(ctx.store, user.id, limit=30)
    included = {shot.id for shot in shots}
    required = {
        shot_id
        for experiment in experiments
        for shot_id in [experiment.reference_shot_id, *experiment.result_shot_ids]
        if shot_id
    }
    required.update(
        direction.source_shot_id
        for direction in directions
        if direction.source_shot_id
    )
    if sessions and sessions[0].representative_result_shot_id:
        required.add(sessions[0].representative_result_shot_id)
    for shot_id in sorted(required - included):
        shot = await repo.find_shot(ctx.store, shot_id)
        if shot is not None and shot.user_id == user.id and not shot.superseded_by_inspiration_id:
            shots.append(shot)
    value = MobileSnapshot(
        user=user,
        drive_connected=bool(user.drive_folder_id),
        drive_folder_url=(
            f"https://drive.google.com/drive/folders/{user.drive_folder_id}"
            if user.drive_folder_id and user.drive_folder_id != "local"
            else ""
        ),
        open_experiment=await repo.open_experiment(ctx.store, user.id),
        latest_capture_session=sessions[0] if sessions else None,
        latest_run=runs[0] if runs else None,
        latest_shoot=await shoots.latest(ctx, user.id),
        latest_shoot_record=await shoots.latest_record(ctx, user.id),
        latest_shot=await shot_api._shot_view(ctx, shots[0]) if shots else None,
        recent_shots=shots,
        recent_inspirations=await repo.list_inspirations(ctx.store, user.id, limit=30),
        photographer_signals=await repo.list_photographer_signals(ctx.store, user.id),
        journey=await repo.list_journey_updates(ctx.store, user.id, limit=10),
        profile=await shot_api.profile(session_user, ctx),
        techniques=await experiment_api.technique_map(session_user, ctx),
        technique_catalogue=await experiment_api.technique_catalogue(session_user, ctx),
        experiments=experiments,
        experiment_directions=directions,
        latest_deconstruction=deconstructions[0] if deconstructions else None,
        recent_scout_answers=await repo.list_scout_answers(ctx.store, user.id, limit=20),
        recent_interventions=await repo.list_interventions(ctx.store, user.id, limit=20),
    )
    encoded = jsonable_encoder(value)
    # Building the Profile stamps when this read occurred. That timestamp is
    # not a data change and must not defeat an otherwise useful mobile cache.
    etag_value = dict(encoded)
    etag_value["profile"] = dict(encoded["profile"])
    etag_value["profile"]["provenance"] = dict(encoded["profile"]["provenance"])
    etag_value["profile"]["provenance"].pop("computed_at", None)
    digest = hashlib.sha256(
        json.dumps(etag_value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:24]
    etag = f'"{digest}"'
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return JSONResponse(encoded, headers={"ETag": etag})
