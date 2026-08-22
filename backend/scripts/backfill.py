"""Backfill: sync every connected folder and run the pipeline to completion.

    uv run python scripts/backfill.py

The Cloud Run Job form of the daily tick, minus the Scout: it only makes
sure every file in every folder has been ingested, analysed and mapped. Uses
the same wiring as the server (``api.deps``), so whatever ports the
environment selects (local or cloud) are the ones used here.
"""

import asyncio

from app.api import deps
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.services import ingest


async def main() -> None:
    ctx = deps.get_context()
    total = 0
    for user in await repo.list_users(ctx.store):
        created = await ingest.sync(ctx, user)
        total += len(created)
        print(f"{user.email}: queued {len(created)}")
    if isinstance(ctx.bus, InProcessBus):
        await ctx.bus.drain()
    print(f"done: {total} new shots")


if __name__ == "__main__":
    asyncio.run(main())
