"""Technique Map and Experiments for the dashboard, plus the human gate (skip)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import current_user
from app.api.deps import get_context
from app.domain import taxonomy
from app.domain.entities import Experiment, TechniqueState, TechniqueStatus
from app.infra import repository as repo
from app.services import scout
from app.services.context import Context

router = APIRouter(prefix="/api", tags=["experiments"])


class TechniqueNode(BaseModel):
    technique_id: str
    name: str
    family: str
    level: int
    requires: list[str]
    status: TechniqueStatus
    attempts: int
    #: How many of those more than one lens saw and meant.
    corroborated: int
    last_observed: str | None
    unlocked: bool


@router.get("/techniques", response_model=list[TechniqueNode])
async def technique_map(
    session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)
):
    """Every Technique with the photographer's record filled in.

    No score crosses this boundary (decision 46): what is reported is how often
    the Evidence saw it and how often more than one lens agreed.
    """
    states = {s.technique_id: s for s in await repo.list_skills(ctx.store, session_user["id"])}
    observed = {tid for tid, s in states.items() if s.status is not TechniqueStatus.UNOBSERVED}
    nodes = []
    for t in taxonomy.TECHNIQUES:
        s = states.get(t.id) or TechniqueState(user_id=session_user["id"], technique_id=t.id)
        nodes.append(
            TechniqueNode(
                technique_id=t.id,
                name=t.name,
                family=t.family.value,
                level=t.level,
                requires=list(t.requires),
                status=s.status,
                attempts=s.attempts,
                corroborated=s.corroborated,
                last_observed=s.last_observed.isoformat() if s.last_observed else None,
                unlocked=all(r in observed for r in t.requires),
            )
        )
    return nodes


@router.post("/techniques/rebuild")
async def rebuild_technique_map(
    session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)
):
    """Re-derive the map from stored analyses. The Cartographer is pure and
    idempotent on shot id, so this is safe any time and proves decision 3:
    the model produces evidence, only the rules move the map."""
    from app.services import cartographer

    shots = await repo.list_shots(ctx.store, session_user["id"])
    applied = 0
    for shot in shots:
        if shot.status.value == "analyzed":
            await cartographer.update(ctx, {"shot_id": shot.id})
            applied += 1
    skills = await repo.list_skills(ctx.store, session_user["id"])
    return {"shots_applied": applied, "techniques": len(skills)}


@router.get("/experiments", response_model=list[Experiment])
async def list_experiments(
    limit: int = 20,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    return await repo.list_experiments(ctx.store, session_user["id"], limit=limit)


@router.get("/experiments/open", response_model=Experiment | None)
async def open_experiment(
    session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)
):
    return await repo.open_experiment(ctx.store, session_user["id"])


@router.post("/experiments/issue", response_model=Experiment | None)
async def issue_experiment(
    force: bool = False,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    """Manual trigger. The Scheduler does this daily; the demo does it live."""
    return await scout.issue(ctx, session_user["id"], force=force)


@router.post("/experiments/{experiment_id}/skip", response_model=Experiment)
async def skip_experiment(
    experiment_id: str,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    try:
        return await scout.skip(ctx, session_user["id"], experiment_id)
    except repo.UnknownEntity as exc:
        raise HTTPException(404, "experiment not found") from exc
