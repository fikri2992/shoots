"""Drive push channels: Google tells us when a folder changes.

One channel per connected user, opened by the reader service account on the
user's folder, with the user id as the channel token so ``/drive/notify``
knows whose folder to sync. Channels live at most a day; ``renew_all`` runs
from the Scheduler and replaces any that are near expiry. Polling
(``/tasks/sync``) stays on as the belt to these braces, so a missed
notification costs minutes, not an experiment.
"""

import logging
from datetime import timedelta

from app.config import settings
from app.domain.entities import DriveChannel, User, new_id, now
from app.infra import repository as repo
from app.services.context import Context

logger = logging.getLogger(__name__)

#: Renew when this close to expiry, so a delayed Scheduler run still lands.
RENEW_MARGIN = timedelta(hours=6)


def can_watch() -> bool:
    """Google only delivers to public HTTPS; local dev has no channel at all."""
    return settings.drive_webhook_url.startswith("https://") and not settings.drive_local_folder


def needs_renewal(channel: DriveChannel | None, at=None) -> bool:
    if channel is None:
        return True
    return channel.expires_at <= (at or now()) + RENEW_MARGIN


async def ensure(ctx: Context, user: User, force: bool = False) -> DriveChannel | None:
    """Open a channel for the user's folder if none is live. Returns the live one."""
    if not can_watch() or not user.drive_folder_id:
        return user.drive_channel
    if not force and not needs_renewal(user.drive_channel):
        return user.drive_channel

    if user.drive_channel:
        try:
            await ctx.drive.stop(user.drive_channel.channel_id, user.drive_channel.resource_id)
        except Exception as error:  # noqa: BLE001 — an expired channel cannot be stopped
            logger.info("stop old channel for %s: %s", user.id, str(error)[:120])

    channel = await ctx.drive.watch(
        folder_id=user.drive_folder_id,
        channel_id=new_id("chan"),
        address=settings.drive_webhook_url,
        token=user.id,
        hours=settings.drive_channel_hours,
    )
    user.drive_channel = channel
    await repo.put_user(ctx.store, user)
    await repo.record(
        ctx.store,
        user.id,
        "drive",
        "watching",
        {
            "channel_id": channel.channel_id if channel else "",
            "expires_at": channel.expires_at.isoformat() if channel else "",
        },
    )
    return channel


async def renew_all(ctx: Context) -> int:
    """Scheduler entry point. Returns how many channels were (re)opened."""
    renewed = 0
    for user in await repo.list_writable_users(ctx.store):
        before = user.drive_channel.channel_id if user.drive_channel else ""
        try:
            after = await ensure(ctx, user)
        except Exception:  # one user's folder must not stop the others
            logger.exception("renew channel failed for %s", user.id)
            continue
        if after and after.channel_id != before:
            renewed += 1
    return renewed
