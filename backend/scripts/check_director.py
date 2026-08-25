"""Render the reference clip for the open experiment with the real models.

    uv run python scripts/check_director.py [experiment_id]

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


async def main(experiment_id: str | None) -> None:
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
    experiment = None
    if experiment_id:
        experiment = await repo.get_experiment(store, experiment_id)
    else:
        for user in users:
            experiment = await repo.open_experiment(store, user.id)
            if experiment:
                break
    if experiment is None:
        raise SystemExit("no open experiment; issue one first (scripts/check_scout.py)")
    print(
        f"experiment {experiment.id}: {experiment.title} "
        f"[{experiment.technique_id}] clip={experiment.reference_clip!r}"
    )
    if experiment.reference_clip:
        experiment.reference_clip = ""
        await repo.put_experiment(store, experiment)

    started = time.monotonic()
    path = await director.direct(
        ctx, {"user_id": experiment.user_id, "experiment_id": experiment.id}
    )
    print(f"done in {time.monotonic() - started:.0f}s -> {path}")
    for event in await repo.list_events(store, experiment.user_id, limit=5):
        if event.agent == "director":
            print(f"  {event.stage}: {event.detail}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
