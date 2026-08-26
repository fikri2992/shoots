"""Small explicit Photographer-memory write and correction surface."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.api.auth import current_user
from app.api.deps import get_context
from app.domain.entities import (
    PhotographerSignal,
    PhotographerSignalKind,
    SignalScope,
    SignalSource,
)
from app.infra import repository as repo
from app.services import photographer_memory
from app.services.context import Context

router = APIRouter(prefix="/api/memory", tags=["memory"])


class SignalIn(BaseModel):
    scope: SignalScope = SignalScope.PHOTOGRAPHER
    scope_id: str = ""
    kind: PhotographerSignalKind
    value: str = Field(min_length=1, max_length=500)
    supersedes_signal_id: str = ""
    expires_at: datetime | None = None


@router.get("/signals", response_model=list[PhotographerSignal])
async def list_signals(
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> list[PhotographerSignal]:
    return await repo.list_photographer_signals(ctx.store, session_user["id"])


@router.post("/signals", response_model=PhotographerSignal)
async def add_signal(
    body: SignalIn,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> PhotographerSignal:
    if body.kind is PhotographerSignalKind.SOURCE_ROLE:
        raise HTTPException(409, "Use the Mine/Inspiration correction action")
    provenance = f"api:{body.supersedes_signal_id or 'new'}"
    signal_id = photographer_memory.stable_signal_id(
        session_user["id"],
        body.scope,
        body.scope_id,
        body.kind,
        body.value,
        provenance,
    )
    signal = PhotographerSignal(
        id=signal_id,
        user_id=session_user["id"],
        scope=body.scope,
        scope_id=body.scope_id,
        kind=body.kind,
        value=body.value,
        source=SignalSource.PHOTOGRAPHER_ACTION,
        source_event_id=f"evt_{signal_id}_signal_stored",
        supersedes_signal_id=body.supersedes_signal_id,
        expires_at=body.expires_at,
    )
    try:
        return await photographer_memory.apply_photographer_signal(ctx, signal)
    except photographer_memory.SignalConflict as exc:
        raise HTTPException(409, str(exc)) from exc


@router.delete("/signals/{signal_id}", status_code=204)
async def remove_signal(
    signal_id: str,
    session_user: dict[str, str] = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Response:
    try:
        await photographer_memory.retract(ctx, session_user["id"], signal_id)
    except repo.UnknownEntity as exc:
        raise HTTPException(404, "Photographer Signal not found") from exc
    return Response(status_code=204)
