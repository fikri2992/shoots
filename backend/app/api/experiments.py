"""Technique Map and Experiments for the dashboard, plus the human gate (skip)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import current_user
from app.api.deps import get_context
from app.domain import taxonomy
from app.domain.entities import Experiment, TechniqueStatus
from app.infra import repository as repo
from app.services import scout
from app.services.context import Context

router = APIRouter(prefix="/api", tags=["experiments"])


class TechniqueNode(BaseModel):
    technique_id: str
    name: str
    family: str
    status: TechniqueStatus
    attempts: int
    #: How many of those more than one lens saw and meant.
    corroborated: int
    last_observed: str | None


@router.get("/techniques", response_model=list[TechniqueNode])
async def technique_map(
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> list[TechniqueNode]:
    """Every Technique with the photographer's record filled in.

    No score crosses this boundary (decision 61): what is reported is how often
    the Evidence saw it and how often more than one lens agreed.
    """
    states = {
        state.technique_id: state
        for state in await repo.list_technique_states(ctx.store, session_user["id"])
    }
    nodes = []
    for technique_id, state in sorted(states.items()):
        if state.status is TechniqueStatus.UNOBSERVED or state.attempts <= 0:
            continue
        technique = taxonomy.BY_ID.get(technique_id)
        if technique is None:
            continue
        nodes.append(
            TechniqueNode(
                technique_id=technique.id,
                name=technique.name,
                family=technique.family.value,
                status=state.status,
                attempts=state.attempts,
                corroborated=state.corroborated,
                last_observed=state.last_observed.isoformat() if state.last_observed else None,
            )
        )
    return nodes


@router.post("/techniques/rebuild")
async def rebuild_technique_map(
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> dict[str, int]:
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
    states = await repo.list_technique_states(ctx.store, session_user["id"])
    return {"shots_applied": applied, "techniques": len(states)}


@router.get("/experiments", response_model=list[Experiment])
async def list_experiments(
    limit: int = 20,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> list[Experiment]:
    return await repo.list_experiments(ctx.store, session_user["id"], limit=limit)


@router.get("/experiments/open", response_model=Experiment | None)
async def open_experiment(
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Experiment | None:
    return await repo.open_experiment(ctx.store, session_user["id"])


@router.post("/experiments/issue", response_model=Experiment | None)
async def issue_experiment(
    force: bool = False,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Experiment | None:
    """Ask Scout to check for a supported Direction now. Silence returns null."""
    return await scout.issue(ctx, session_user["id"], force=force)


@router.post("/experiments/{experiment_id}/skip", response_model=Experiment)
async def skip_experiment(
    experiment_id: str,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Experiment:
    try:
        return await scout.skip(ctx, session_user["id"], experiment_id)
    except repo.UnknownEntity as exc:
        raise HTTPException(404, "experiment not found") from exc


@router.post("/experiments/{experiment_id}/leave", response_model=Experiment)
async def leave_experiment(
    experiment_id: str,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Experiment:
    try:
        return await scout.leave(ctx, session_user["id"], experiment_id)
    except repo.UnknownEntity as exc:
        raise HTTPException(404, "experiment not found") from exc
