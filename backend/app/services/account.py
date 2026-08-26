"""Idempotent cleanup for a Photographer who requested account deletion."""

from app.config import settings
from app.infra import repository as repo
from app.infra.drive import UserDrive, user_credentials
from app.infra.storage import user_prefix
from app.services.context import Context


async def delete(ctx: Context, user_id: str) -> None:
    user = await repo.find_user(ctx.store, user_id)
    if user is None:
        return
    token = await ctx.tokens.get(user.id)
    if user.drive_channel and ctx.drive is not None:
        await ctx.drive.stop(user.drive_channel.channel_id, user.drive_channel.resource_id)
    if (
        user.drive_folder_id
        and user.drive_folder_id != "local"
        and token
        and settings.drive_service_account
    ):
        await UserDrive(user_credentials(token)).unshare_with(
            user.drive_folder_id, settings.drive_service_account
        )
    await ctx.tokens.delete(user.id)
    await ctx.blobs.delete_prefix(user_prefix(user.id))
    await repo.delete_user_records(ctx.store, user.id)
