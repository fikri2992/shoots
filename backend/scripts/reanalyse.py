"""Re-run the Analyst panel over stored shots, keeping everything else.

    uv run python scripts/reanalyse.py [shot_id ...]

Stop the dev server first (two processes on one store.json lose writes).
Only the Analyst stage runs, on a bare context with no bus subscribers, so
the Cartographer does not count the same shot twice and no verdict moves.
Afterwards, rebuild the Technique Map from the new Analyses:

    uv run python scripts/call_as_user.py POST api/techniques/rebuild
"""

import asyncio
import sys
import time

from app.config import settings
from app.domain.entities import ShotStatus
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.drive import LocalDriveClient
from app.infra.secrets import LocalTokenStore
from app.infra.storage import LocalBlobStore
from app.infra.store import FileStore
from app.services import analyst
from app.services.context import Context


async def main(shot_ids: list[str]) -> None:
    store = FileStore(settings.blob_root + "/store.json")
    ctx = Context(
        store=store,
        blobs=LocalBlobStore(),
        bus=InProcessBus(),  # no subscribers: the panel runs, nothing downstream does
        drive=LocalDriveClient("."),
        tokens=LocalTokenStore(),
    )
    shots = []
    for user in await repo.list_users(store):
        shots += [
            s
            for s in await repo.list_shots(store, user.id)
            if s.status is ShotStatus.ANALYZED and (not shot_ids or s.id in shot_ids)
        ]
    print(f"re-analysing {len(shots)} shot(s)")
    for shot in shots:
        shot.status = ShotStatus.INGESTED
        await repo.put_shot(store, shot)
        started = time.monotonic()
        try:
            await analyst.analyse(ctx, {"shot_id": shot.id})
        except Exception as error:  # noqa: BLE001 — report, keep going
            print(f"  {shot.filename}: FAILED {type(error).__name__}: {str(error)[:160]}")
            shot.status = ShotStatus.ANALYZED
            await repo.put_shot(store, shot)
            continue
        analysis = await repo.find_analysis(store, shot.id)
        seen = ", ".join(f"{t.technique_id} x{t.agreement}" for t in analysis.techniques)
        lost = ", ".join(
            f"{d['lens']} {d['technique_id']} {d['confidence']}" for d in analysis.dissent
        )
        print(
            f"  {shot.filename}: {len(analysis.techniques)} techniques "
            f"in {time.monotonic() - started:.0f}s · {seen}"
        )
        if lost:
            print(f"    not counted: {lost}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main(sys.argv[1:]))
