"""Write one review back into the real Drive folder.

    uv run python scripts/check_scribe.py [shot_id]

Uses the dev FileStore and the stored user token, so stop the dev server
first (two processes on one store.json lose writes). Picks the newest
analysed shot without a review unless a shot id is given, and prints the
Drive link of the file it wrote.
"""

import asyncio
import sys

from app.config import settings
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.drive import LocalDriveClient
from app.infra.secrets import LocalTokenStore
from app.infra.storage import LocalBlobStore
from app.infra.store import FileStore
from app.services import scribe
from app.services.context import Context


async def main(shot_id: str | None) -> None:
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
    shots = await repo.list_shots(store, users[0].id)
    shot = next((s for s in shots if s.id == shot_id), None) if shot_id else None
    if shot is None:
        shot = next(s for s in shots if s.status.value == "analyzed" and not s.drive_review_id)
    print(f"shot {shot.id} {shot.filename} quest={shot.quest_id or '-'}")
    file_id = await scribe.write_review(ctx, {"shot_id": shot.id})
    shot = await repo.get_shot(store, shot.id)
    print(f"wrote {file_id}\n{shot.drive_review_url}")
    for event in await repo.list_events(store, shot.user_id, limit=3):
        if event.agent == "scribe":
            print(f"  {event.stage}: {event.detail}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
