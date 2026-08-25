"""Read side for the dashboard: shots, events, blobs. Signed-in user only."""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.api.auth import current_user
from app.api.deps import get_context
from app.domain import tendency
from app.domain.entities import ActivityEvent, Analysis, JourneyUpdate, Shot, User, now
from app.infra import repository as repo
from app.infra.storage import content_type_for, user_prefix
from app.services import journey as journey_service
from app.services.context import Context

router = APIRouter(prefix="/api", tags=["shots"])


@router.get("/me", response_model=User | None)
async def me(session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)):
    return await repo.find_user(ctx.store, session_user["id"])


class ShotView(BaseModel):
    shot: Shot
    analysis: Analysis | None = None


@router.get("/shots", response_model=list[ShotView])
async def list_shots(
    limit: int = 100,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    shots = await repo.list_shots(ctx.store, session_user["id"], limit=limit)
    views = []
    for shot in shots:
        analysis = await repo.find_analysis(ctx.store, shot.id) if shot.analyzed_at else None
        views.append(ShotView(shot=shot, analysis=analysis))
    return views


@router.get("/shots/{shot_id}", response_model=ShotView)
async def get_shot(
    shot_id: str, session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)
):
    shot = await repo.find_shot(ctx.store, shot_id)
    if shot is None or shot.user_id != session_user["id"]:
        raise HTTPException(404, "shot not found")
    return ShotView(shot=shot, analysis=await repo.find_analysis(ctx.store, shot.id))


class KeeperIn(BaseModel):
    """``true`` marks the Shot valued; ``false`` returns it to unknown."""

    keeper: bool


@router.put("/shots/{shot_id}/keeper", response_model=Shot)
async def set_keeper(
    body: KeeperIn,
    shot_id: str,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    """One optional tap: the photographer marks a shot worth keeping.

    The only taste signal in the system. It separates "you do this often",
    which the Tendency Profile measures on its own, from "this is what you
    value", which nothing else here can supply. It is not a score, it promotes
    nothing, and it is never second-guessed.

    Positive only (decision 45): unmarking clears the mark and returns the Shot
    to *unknown*. It does not record a rejection, because the photographer did
    not give one - and a hobbyist who marks four frames out of two hundred has
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
    return shot


class BucketView(BaseModel):
    bucket: str
    count: int
    #: How much likelier this bucket is to be kept than the photographer's
    #: average. Null until they have marked enough to mean anything.
    keeper_lift: float | None = None


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


class ProfileView(BaseModel):
    """The Tendency Profile, as the Journey page draws it. Counts first."""

    shots: int
    keepers: int
    taste_is_known: bool
    dimensions: list[DimensionView]
    scenes: int
    frames_per_scene: float
    walks_on: bool
    blind_spots: list[str]
    #: What the photographer's own work suggests trying, with its citation.
    challenge: str = ""
    challenge_source: str = ""


@router.get("/profile", response_model=ProfileView)
async def profile(
    session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)
):
    built = await journey_service.profile_now(ctx, session_user["id"])
    challenge = tendency.challenge_for(built)
    return ProfileView(
        shots=built.shots,
        keepers=built.keepers,
        taste_is_known=built.taste_is_known,
        scenes=built.dwell.scenes,
        frames_per_scene=round(built.dwell.per_scene, 2),
        walks_on=built.dwell.walks_on,
        blind_spots=list(built.blind_spots),
        challenge=challenge.citation if challenge else "",
        challenge_source=challenge.source if challenge else "",
        dimensions=[
            DimensionView(
                id=dim.id,
                label=dim.label,
                unreadable=p.unreadable,
                exploration=round(p.exploration, 3),
                readable=p.readable,
                narrow=p.narrow,
                dominant=p.dominant,
                never=list(p.unexplored),
                buckets=[
                    BucketView(
                        bucket=bucket,
                        count=p.counts.get(bucket, 0),
                        keeper_lift=(
                            round(lift, 2)
                            if (lift := p.keeper_lift(bucket, built.keeper_rate)) is not None
                            else None
                        ),
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
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    """The agent's conclusions about this photographer, newest first."""
    return await repo.list_journey_updates(ctx.store, session_user["id"], limit=limit)


@router.get("/events", response_model=list[ActivityEvent])
async def list_events(
    limit: int = 100,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    return await repo.list_events(ctx.store, session_user["id"], limit=limit)


@router.get("/blobs/{path:path}")
async def blob(
    path: str, session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)
):
    """Blobs are namespaced by user id; the prefix check is the whole ACL."""
    if not path.startswith(user_prefix(session_user["id"])) or ".." in path:
        raise HTTPException(404, "not found")
    if not await ctx.blobs.exists(path):
        raise HTTPException(404, "not found")
    data = await ctx.blobs.read(path)
    return Response(
        data,
        media_type=content_type_for(path, data),
        headers={"Cache-Control": "private, max-age=3600"},
    )
