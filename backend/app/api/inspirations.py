"""Explicit Mine/Inspiration authority and current Inspiration reads."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import current_user
from app.api.deps import get_context
from app.domain.entities import Inspiration, SourceRole
from app.infra import repository as repo
from app.services import source_authority
from app.services.context import Context

router = APIRouter(prefix="/api", tags=["inspirations"])


class SourceRoleIn(BaseModel):
    source_role: SourceRole


class SourceRoleResult(BaseModel):
    source_role: SourceRole
    shot_id: str = ""
    inspiration_id: str = ""


@router.get("/inspirations", response_model=list[Inspiration])
async def list_inspirations(
    limit: int = 30,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> list[Inspiration]:
    return await repo.list_inspirations(
        ctx.store,
        session_user["id"],
        limit=max(1, min(limit, 100)),
    )


@router.put("/shots/{shot_id}/source-role", response_model=SourceRoleResult)
async def set_shot_source_role(
    shot_id: str,
    body: SourceRoleIn,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> SourceRoleResult:
    shot = await repo.find_shot(ctx.store, shot_id)
    if shot is None or shot.user_id != session_user["id"]:
        raise HTTPException(404, "Shot not found")
    if body.source_role is SourceRole.MINE:
        if not shot.superseded_by_inspiration_id:
            return SourceRoleResult(source_role=SourceRole.MINE, shot_id=shot.id)
        restored = await source_authority.inspiration_to_shot(
            ctx,
            session_user["id"],
            shot.superseded_by_inspiration_id,
        )
        return SourceRoleResult(source_role=SourceRole.MINE, shot_id=restored.id)
    try:
        inspiration = await source_authority.shot_to_inspiration(
            ctx,
            session_user["id"],
            shot.id,
        )
    except source_authority.SourceRoleConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    return SourceRoleResult(
        source_role=SourceRole.INSPIRATION,
        inspiration_id=inspiration.id,
    )


@router.put("/inspirations/{inspiration_id}/source-role", response_model=SourceRoleResult)
async def set_inspiration_source_role(
    inspiration_id: str,
    body: SourceRoleIn,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> SourceRoleResult:
    inspiration = await repo.find_inspiration(ctx.store, inspiration_id)
    if inspiration is None or inspiration.user_id != session_user["id"]:
        raise HTTPException(404, "Inspiration not found")
    if body.source_role is SourceRole.INSPIRATION and not inspiration.superseded_at:
        return SourceRoleResult(
            source_role=SourceRole.INSPIRATION,
            inspiration_id=inspiration.id,
        )
    shot = await source_authority.inspiration_to_shot(ctx, session_user["id"], inspiration.id)
    return SourceRoleResult(source_role=SourceRole.MINE, shot_id=shot.id)
