"""Read side for the dashboard: shots, events, blobs. Signed-in user only."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.api.auth import current_user
from app.api.deps import get_context
from app.domain import tendency
from app.domain.entities import (
    ActivityEvent,
    Analysis,
    Composition,
    Finding,
    JourneyUpdate,
    Provenance,
    Run,
    Shot,
    TechniqueEvidence,
    User,
    now,
)
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.infra.storage import content_type_for, requested_user_path
from app.services import journey as journey_service
from app.services import profile as profile_service
from app.services.context import Context

router = APIRouter(prefix="/api", tags=["shots"])


@router.get("/me", response_model=User | None)
async def me(
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> User | None:
    return await repo.find_user(ctx.store, session_user["id"])


class AnalysisView(BaseModel):
    """The Analyst's read, as a photographer may see it.

    Listed field by field rather than returning ``Analysis`` whole. Scores are
    not stored (decision 61), and new internal fields still need an explicit
    read-side decision before they cross this boundary.

    Naming what crosses the boundary also means the next field added to
    ``Analysis`` has to be let out deliberately instead of arriving on its own.
    """

    shot_id: str
    model: str
    prompt_version: str
    techniques: list[TechniqueEvidence] = Field(default_factory=list)
    composition: Composition = Field(default_factory=Composition)
    observations: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    critique: str = ""
    panel: dict[str, float] = Field(default_factory=dict)
    dissent: list[dict[str, object]] = Field(default_factory=list)
    abstained: str = ""
    created_at: datetime

    @classmethod
    def of(cls, analysis: Analysis | None) -> "AnalysisView | None":
        return None if analysis is None else cls(**analysis.model_dump())


class ShotView(BaseModel):
    shot: Shot
    analysis: AnalysisView | None = None


@router.get("/shots", response_model=list[ShotView])
async def list_shots(
    limit: int = 100,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> list[ShotView]:
    shots = await repo.list_shots(ctx.store, session_user["id"], limit=limit)
    views = []
    for shot in shots:
        analysis = await repo.find_analysis(ctx.store, shot.id) if shot.analyzed_at else None
        views.append(ShotView(shot=shot, analysis=AnalysisView.of(analysis)))
    return views


@router.get("/shots/{shot_id}", response_model=ShotView)
async def get_shot(
    shot_id: str,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> ShotView:
    shot = await repo.find_shot(ctx.store, shot_id)
    if shot is None or shot.user_id != session_user["id"]:
        raise HTTPException(404, "shot not found")
    analysis = await repo.find_analysis(ctx.store, shot.id)
    return ShotView(shot=shot, analysis=AnalysisView.of(analysis))


class KeeperIn(BaseModel):
    """``true`` marks the Shot valued; ``false`` returns it to unknown."""

    keeper: bool


@router.put("/shots/{shot_id}/keeper", response_model=Shot)
async def set_keeper(
    body: KeeperIn,
    shot_id: str,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Shot:
    """One optional tap: the photographer marks a shot worth keeping.

    The only taste signal in the system. It separates "you do this often",
    which the Tendency Profile measures on its own, from "this is what you
    value", which nothing else here can supply. It is not a score, it promotes
    nothing, and it is never second-guessed.

    Positive only (decision 45): unmarking clears the mark and returns the Shot
    to *unknown*. It does not record a rejection, because the photographer did
    not give one - and a hobbyist who marks four Shots out of two hundred has
    not disliked the other hundred and ninety-six.
    """
    shot = await repo.find_shot(ctx.store, shot_id)
    if shot is None or shot.user_id != session_user["id"]:
        raise HTTPException(404, "shot not found")
    if bool(shot.kept_at) != body.keeper:
        shot.kept_at = now() if body.keeper else None
        await repo.put_shot(ctx.store, shot)
        await repo.record(
            ctx.store,
            shot.user_id,
            "photographer",
            "kept" if body.keeper else "unkept",
            {"filename": shot.filename},
            shot_id=shot.id,
        )
        await ctx.bus.publish(
            TOPICS["keeper.changed"],
            {"user_id": shot.user_id, "shot_id": shot.id, "keeper": body.keeper},
        )
    return shot


class BucketView(BaseModel):
    bucket: str
    count: int
    keepers: int = 0


class DimensionView(BaseModel):
    id: str
    label: str
    buckets: list[BucketView]
    unreadable: int
    #: 0 when every shot landed in one bucket, 1 when spread evenly.
    exploration: float
    #: False when there are too few shots to claim anything beyond the counts.
    readable: bool
    narrow: bool
    dominant: str
    never: list[str]
    source: str
    readable_keepers: int


class ProfileView(BaseModel):
    """The Tendency Profile, as the Journey page draws it. Counts first."""

    shots: int
    keepers: int
    taste_is_known: bool
    #: Which arithmetic produced these figures. Two profiles under different
    #: versions are not comparable and must not be diffed.
    calc_version: str
    dimensions: list[DimensionView]
    scenes: int
    shots_per_scene: float
    walks_on: bool
    blind_spots: list[str]
    provenance: Provenance


@router.get("/profile", response_model=ProfileView)
async def profile(
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> ProfileView:
    built = await journey_service.profile_now(ctx, session_user["id"])
    return ProfileView(
        shots=built.shots,
        keepers=built.keepers,
        taste_is_known=built.taste_is_known,
        calc_version=built.calc_version,
        scenes=built.dwell.scenes,
        shots_per_scene=round(built.dwell.per_scene, 2),
        walks_on=built.dwell.walks_on,
        blind_spots=list(built.blind_spots),
        provenance=profile_service.provenance(built),
        dimensions=[
            DimensionView(
                id=dim.id,
                label=dim.label,
                unreadable=p.unreadable,
                exploration=round(p.exploration, 3),
                readable=p.readable,
                narrow=p.narrow,
                dominant=p.dominant,
                never=list(p.never_used),
                source=dim.source,
                readable_keepers=p.readable_keepers,
                buckets=[
                    BucketView(
                        bucket=bucket,
                        count=p.counts.get(bucket, 0),
                        keepers=p.keepers.get(bucket, 0),
                    )
                    for bucket in dim.buckets
                ],
            )
            for dim in tendency.DIMENSIONS
            if (p := built.dimensions[dim.id])
        ],
    )


@router.get("/journey", response_model=list[JourneyUpdate])
async def journey_updates(
    limit: int = 20,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> list[JourneyUpdate]:
    """The agent's conclusions about this photographer, newest first."""
    return await repo.list_journey_updates(ctx.store, session_user["id"], limit=limit)


@router.get("/events", response_model=list[ActivityEvent])
async def list_events(
    limit: int = 100,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> list[ActivityEvent]:
    return await repo.list_events(ctx.store, session_user["id"], limit=limit)


@router.get("/runs", response_model=list[Run])
async def list_runs(
    limit: int = 20,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> list[Run]:
    """Durable completion state. ActivityEvents remain the explanation."""
    return await repo.list_runs(ctx.store, session_user["id"], limit=limit)


class LatestRunView(BaseModel):
    run: Run | None


@router.get("/runs/latest", response_model=LatestRunView)
async def latest_run(
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> LatestRunView:
    found = await repo.list_runs(ctx.store, session_user["id"], limit=1)
    return LatestRunView(run=found[0] if found else None)


@router.get("/blobs/{path:path}")
async def blob(
    path: str,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Response:
    """Blobs are namespaced by user id; the prefix check is the whole ACL."""
    stored_path = requested_user_path(session_user["id"], path)
    if not stored_path or ".." in stored_path:
        raise HTTPException(404, "not found")
    if not await ctx.blobs.exists(stored_path):
        raise HTTPException(404, "not found")
    data = await ctx.blobs.read(stored_path)
    return Response(
        data,
        media_type=content_type_for(stored_path, data),
        headers={"Cache-Control": "private, max-age=3600"},
    )
