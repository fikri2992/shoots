"""Render the reference clip for the open quest with the real models.

    uv run python scripts/check_director.py [quest_id]

Uses the dev FileStore and LocalBlobStore, so the dashboard plays the clip
afterwards. Prints the storyboard, timing and the blob path.
"""

import asyncio
import sys
import time

from app.config import settings
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.drive import LocalDriveClient
from app.infra.secrets import LocalTokenStore
from app.infra.storage import LocalBlobStore
from app.infra.store import FileStore
from app.services import director
from app.services.context import Context


async def main(quest_id: str | None) -> None:
    store = FileStore(settings.blob_root + "/store.json")
    ctx = Context(
        store=store,
        blobs=LocalBlobStore(),
        bus=InProcessBus(),
        drive=LocalDriveClient("."),
        tokens=LocalTokenStore(),
    )
    users = await repo.list_users(store)
    if not users:
        raise SystemExit("no users in the store; sign in to the dev server first")
    quest = None
    if quest_id:
        quest = await repo.get_quest(store, quest_id)
    else:
        for user in users:
            quest = await repo.open_quest(store, user.id)
            if quest:
                break
    if quest is None:
        raise SystemExit("no open quest; issue one first (scripts/check_scout.py)")
    print(f"quest {quest.id}: {quest.title} [{quest.technique_id}] clip={quest.reference_clip!r}")
    if quest.reference_clip:
        quest.reference_clip = ""
        await repo.put_quest(store, quest)

    started = time.monotonic()
    path = await director.direct(ctx, {"user_id": quest.user_id, "quest_id": quest.id})
    print(f"done in {time.monotonic() - started:.0f}s -> {path}")
    for event in await repo.list_events(store, quest.user_id, limit=5):
        if event.agent == "director":
            print(f"  {event.stage}: {event.detail}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
