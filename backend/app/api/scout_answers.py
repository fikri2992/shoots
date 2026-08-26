"""One-tap Photographer answers to stored Scout Questions."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import current_user
from app.api.deps import get_context
from app.domain.entities import ScoutAnswer
from app.infra import repository as repo
from app.services import scout_answers
from app.services.context import Context

router = APIRouter(prefix="/api/shoots", tags=["shoots"])


class AnswerIn(BaseModel):
    revision: int = Field(ge=1)
    option_id: str = Field(min_length=1, max_length=120)


@router.post("/{shoot_id}/scout-answer", response_model=ScoutAnswer)
async def answer(
    shoot_id: str,
    body: AnswerIn,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> ScoutAnswer:
    try:
        return await scout_answers.answer(
            ctx,
            session_user["id"],
            shoot_id,
            body.revision,
            body.option_id,
        )
    except scout_answers.AnswerConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except repo.UnknownEntity as exc:
        raise HTTPException(404, str(exc)) from exc
