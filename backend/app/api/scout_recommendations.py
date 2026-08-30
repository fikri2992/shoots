from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import current_user
from app.api.deps import get_context
from app.domain.entities import (
    Experiment,
    InterventionRecord,
    ScoutRecommendationAction,
)
from app.infra import repository as repo
from app.services import scout_recommendations
from app.services.context import Context

router = APIRouter(prefix="/api/shoots", tags=["shoots"])


class RecommendationIn(BaseModel):
    revision: int = Field(ge=1)
    action: ScoutRecommendationAction
    option_id: str = Field(default="", max_length=120)


class RecommendationResult(BaseModel):
    intervention: InterventionRecord
    experiment: Experiment | None = None


@router.post("/{shoot_id}/scout-recommendation", response_model=RecommendationResult)
async def respond(
    shoot_id: str,
    body: RecommendationIn,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> RecommendationResult:
    try:
        intervention, experiment = await scout_recommendations.respond(
            ctx,
            session_user["id"],
            shoot_id,
            body.revision,
            body.action,
            body.option_id,
        )
    except repo.UnknownEntity as exc:
        raise HTTPException(404, "Shoot Record not found") from exc
    except scout_recommendations.RecommendationConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    return RecommendationResult(intervention=intervention, experiment=experiment)
