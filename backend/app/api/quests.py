"""Skill graph and quests for the dashboard, plus the human gate (skip)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import current_user
from app.api.deps import get_context
from app.domain import taxonomy
from app.domain.entities import Quest, SkillState, SkillStatus
from app.infra import repository as repo
from app.services import scout
from app.services.context import Context

router = APIRouter(prefix="/api", tags=["quests"])


class SkillNode(BaseModel):
    technique_id: str
    name: str
    family: str
    level: int
    requires: list[str]
    status: SkillStatus
    attempts: int
    best_score: int
    last_practiced: str | None
    unlocked: bool


@router.get("/skills", response_model=list[SkillNode])
async def skill_graph(
    session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)
):
    """Every technique, with the user's state filled in. The dashboard's map."""
    states = {s.technique_id: s for s in await repo.list_skills(ctx.store, session_user["id"])}
    attempted = {tid for tid, s in states.items() if s.status is not SkillStatus.UNEXPLORED}
    nodes = []
    for t in taxonomy.TECHNIQUES:
        s = states.get(t.id) or SkillState(user_id=session_user["id"], technique_id=t.id)
        nodes.append(
            SkillNode(
                technique_id=t.id,
                name=t.name,
                family=t.family.value,
                level=t.level,
                requires=list(t.requires),
                status=s.status,
                attempts=s.attempts,
                best_score=s.best_score,
                last_practiced=s.last_practiced.isoformat() if s.last_practiced else None,
                unlocked=all(r in attempted for r in t.requires),
            )
        )
    return nodes


@router.post("/skills/rebuild")
async def rebuild_skills(
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


@router.get("/quests", response_model=list[Quest])
async def list_quests(
    limit: int = 20,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    return await repo.list_quests(ctx.store, session_user["id"], limit=limit)


@router.get("/quests/open", response_model=Quest | None)
async def open_quest(
    session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)
):
    return await repo.open_quest(ctx.store, session_user["id"])


@router.post("/quests/issue", response_model=Quest | None)
async def issue_quest(
    force: bool = False,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
):
    """Manual trigger. The Scheduler does this daily; the demo does it live."""
    return await scout.issue(ctx, session_user["id"], force=force)


@router.post("/quests/{quest_id}/skip", response_model=Quest)
async def skip_quest(
    quest_id: str, session_user: dict = Depends(current_user), ctx: Context = Depends(get_context)
):
    try:
        return await scout.skip(ctx, session_user["id"], quest_id)
    except repo.UnknownEntity as exc:
        raise HTTPException(404, "quest not found") from exc
