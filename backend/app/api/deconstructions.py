"""Photographer-controlled Deconstruction preparation and retrieval."""

from io import BytesIO
from zipfile import ZIP_STORED, ZipFile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.auth import current_user
from app.api.deps import get_context
from app.domain.entities import Deconstruction, DeconstructionSourceType
from app.infra import repository as repo
from app.services import deconstructions
from app.services.context import Context

router = APIRouter(prefix="/api/deconstructions", tags=["deconstructions"])


class PrepareIn(BaseModel):
    source_type: DeconstructionSourceType
    source_id: str = Field(min_length=1, max_length=160)
    source_revision: int = Field(default=0, ge=0)
    cover_shot_id: str = Field(default="", max_length=160)


@router.post("", response_model=Deconstruction)
async def prepare(
    body: PrepareIn,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Deconstruction:
    try:
        return await deconstructions.prepare(
            ctx,
            session_user["id"],
            body.source_type,
            body.source_id,
            body.source_revision,
            body.cover_shot_id,
        )
    except deconstructions.DeconstructionConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except repo.UnknownEntity as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{draft_id}", response_model=Deconstruction)
async def get_draft(
    draft_id: str,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Deconstruction:
    draft = await repo.find_deconstruction(ctx.store, draft_id)
    if draft is None or draft.user_id != session_user["id"]:
        raise HTTPException(404, "Deconstruction not found")
    return draft


@router.get("/{draft_id}/download")
async def download_story(
    draft_id: str,
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> Response:
    draft = await repo.find_deconstruction(ctx.store, draft_id)
    if draft is None or draft.user_id != session_user["id"]:
        raise HTTPException(404, "Story not found")
    if not draft.pages or any(not page.blob_path for page in draft.pages):
        raise HTTPException(409, "Story pages are not ready")

    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        for index, page in enumerate(draft.pages, 1):
            if not await ctx.blobs.exists(page.blob_path):
                raise HTTPException(409, "One or more story pages are unavailable")
            archive.writestr(f"story-{index:02d}.jpg", await ctx.blobs.read(page.blob_path))
        archive.writestr("caption.txt", draft.suggested_caption)
    return Response(
        output.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="shoots-story-{draft.id}.zip"',
            "Cache-Control": "private, no-store",
        },
    )
