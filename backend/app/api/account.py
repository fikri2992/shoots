"""Account deletion with fresh Google reauthentication."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api import auth
from app.api.auth import current_user
from app.api.deps import get_context
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.services.context import Context

router = APIRouter(prefix="/api/account", tags=["account"])


class DeletionAccepted(BaseModel):
    id: str
    status: str


@router.delete("", response_model=DeletionAccepted, status_code=status.HTTP_202_ACCEPTED)
async def delete_account(
    body: auth.AndroidSessionIn,
    claims: dict = Depends(auth.verify_android_token),
    session_user: dict = Depends(current_user),
    ctx: Context = Depends(get_context),
) -> DeletionAccepted:
    if claims.get("sub") != session_user["id"]:
        raise HTTPException(409, "Reauthentication belongs to a different Google account")
    user_id = session_user["id"]
    await repo.request_account_deletion(ctx.store, user_id)
    for device in await repo.list_devices(ctx.store, user_id):
        await repo.delete_device(ctx.store, device["fingerprint"])
    await ctx.bus.publish(TOPICS["account.delete"], {"user_id": user_id})
    return DeletionAccepted(id=user_id, status="requested")
