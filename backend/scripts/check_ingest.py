"""Run Ingest over a local folder and write the outputs where you can look.

    uv run python scripts/check_ingest.py ../data/demo/mine

Uses the real stage code with the directory as the Drive folder, an in-memory
store and blobs under .blobs/check_ingest. Prints one line per shot with the
hard evidence read, and where the gridded frame landed.
"""

import asyncio
import sys
from pathlib import Path

from app.domain.entities import User
from app.infra import repository as repo
from app.infra.bus import TOPICS, InProcessBus
from app.infra.drive import LocalDriveClient
from app.infra.secrets import LocalTokenStore
from app.infra.storage import GRIDDED, LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import ingest
from app.services.context import Context

BLOBS = Path(".blobs/check_ingest")


async def main(folder: str) -> None:
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(BLOBS),
        bus=InProcessBus(),
        drive=LocalDriveClient(folder),
        tokens=LocalTokenStore(BLOBS / "tokens"),
    )

    async def on_new(message):
        await ingest.ingest(ctx, message)

    ctx.bus.subscribe(TOPICS["media.new"], on_new)

    user = User(id="u_check", email="check@local", drive_folder_id="local")
    await repo.put_user(ctx.store, user)
    created = await ingest.sync(ctx, user)
    print(f"queued {len(created)} shots from {folder}")
    await ctx.bus.drain()

    for shot in await repo.list_shots(ctx.store, user.id):
        e = shot.exif
        if shot.video:
            v = shot.video
            evidence = (
                f"{v.width}x{v.height} {v.fps}fps {v.duration_s:.1f}s {v.codec} lufs={v.lufs}"
            )
        else:
            evidence = (
                f"t={e.exposure_time_s} f={e.f_number} iso={e.iso} fl35={e.focal_length_35mm}"
            )
        grid = f"{shot.grid.cols}x{shot.grid.rows}" if shot.grid else "-"
        head = f"{shot.status.value:9} {shot.kind.value:5} {shot.filename:28} grid={grid:5}"
        print(f"{head} {evidence} {shot.error}")
    print(f"gridded frames under {BLOBS / 'users' / user.id / 'shots'}  ({GRIDDED}.png per shot)")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "../data/demo/mine"))
