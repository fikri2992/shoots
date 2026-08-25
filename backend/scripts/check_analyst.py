"""Run Ingest + Analyst over a local folder with the real model.

    uv run python scripts/check_analyst.py ../data/demo/mine [limit]

This is the Analyst's test (AGENTS.md: no mocked Gemini). Prints evidence,
composition read per shot; writes annotated frames under
.blobs/check_analyst so you can look at what the model said.
"""

import asyncio
import sys
from pathlib import Path

from app.domain.entities import User
from app.infra import repository as repo
from app.infra.bus import TOPICS, InProcessBus
from app.infra.drive import LocalDriveClient
from app.infra.secrets import LocalTokenStore
from app.infra.storage import ANNOTATED, LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import analyst, ingest
from app.services.context import Context

BLOBS = Path(".blobs/check_analyst")


async def main(folder: str, limit: int) -> None:
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(BLOBS),
        bus=InProcessBus(),
        drive=LocalDriveClient(folder),
        tokens=LocalTokenStore(BLOBS / "tokens"),
    )

    async def on_new(message):
        await ingest.ingest(ctx, message)

    async def on_ingested(message):
        await analyst.analyse(ctx, message)

    ctx.bus.subscribe(TOPICS["media.new"], on_new)
    ctx.bus.subscribe(TOPICS["media.ingested"], on_ingested)

    user = User(id="u_check", email="check@local", drive_folder_id="local")
    await repo.put_user(ctx.store, user)
    files = await ctx.drive.list_media("local")
    print(f"{len(files)} files in {folder}; analysing up to {limit}")
    ctx.drive = _Limited(ctx.drive, limit)
    await ingest.sync(ctx, user)
    await ctx.bus.drain()

    for shot in await repo.list_shots(ctx.store, user.id):
        analysis = await repo.find_analysis(ctx.store, shot.id)
        print(f"\n=== {shot.filename}  [{shot.status.value}]  {shot.error}")
        if not analysis:
            continue
        agreed = sum(1 for t in analysis.techniques if t.agreement >= 2)
        print(f"corroborated {agreed}/{len(analysis.techniques)}  panel={analysis.panel}")
        for line in analysis.observations:
            print(f"  · {line}")
        for t in analysis.techniques:
            who = "+".join(t.lenses)
            cells = ",".join(t.cells)
            head = f"  {t.technique_id:22} {t.confidence:.2f} x{t.agreement} [{who}]"
            print(f"{head} {cells:12} {t.note}")
        c = analysis.composition
        print(
            f"  subject={c.subject_cells} horizon_row={c.horizon_row} crop={c.suggested_crop_cells}"
        )
        if c.crop_tested:
            kept = "kept" if c.suggested_crop_cells else "rejected"
            print(f"  crop {kept}: {c.crop_before} -> {c.crop_after} in {c.crop_rounds} round(s)")
            print(f"    {c.crop_reason}")
        for m in c.moves:
            print(f"  move: {m.what}: {m.from_cells} -> {m.to_cells}  ({m.reason})")
        print(f"  critique: {analysis.critique}")
        print(f"  annotated: {BLOBS / shot.blobs.get(ANNOTATED, '')}")


class _Limited:
    """Wrap a DriveClient so sync only sees the first N files."""

    def __init__(self, inner, limit: int):
        self._inner, self._limit = inner, limit

    async def list_media(self, folder_id: str):
        return (await self._inner.list_media(folder_id))[: self._limit]

    async def download(self, file_id: str) -> bytes:
        return await self._inner.download(file_id)


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "../data/demo/mine"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    asyncio.run(main(folder, limit))
