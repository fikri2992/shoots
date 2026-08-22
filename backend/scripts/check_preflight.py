"""Pre-flight a local image against the open quest with the real model.

    uv run python scripts/check_preflight.py <image> [quest_id]

Reads the dev store (read-only), prints the checks and the timing.
"""

import asyncio
import pathlib
import sys
import time

from app.agents import preflight
from app.config import settings
from app.domain import taxonomy
from app.imaging import canvas
from app.infra import repository as repo
from app.infra.store import FileStore


async def main(path: str, quest_id: str | None) -> None:
    store = FileStore(settings.blob_root + "/store.json")
    users = await repo.list_users(store)
    quest = None
    if quest_id:
        quest = await repo.get_quest(store, quest_id)
    else:
        for user in users:
            quest = await repo.open_quest(store, user.id)
            if quest:
                break
    if quest is None:
        raise SystemExit("no open quest")
    technique = taxonomy.get(quest.technique_id)
    print(f"quest: {quest.title} [{technique.id}]")
    for c in quest.criteria.text:
        print(f"  - {c}")
    data = pathlib.Path(path).read_bytes()
    preview = canvas.fit_for_model(canvas.load_bytes(data), preflight.PREVIEW_EDGE)
    started = time.monotonic()
    out = await preflight.check(quest, technique, canvas.to_jpeg_bytes(preview, quality=80))
    verdict = "READY" if out.ready else "SHOOT AGAIN"
    print(f"\n{verdict} in {time.monotonic() - started:.1f}s: {out.say}")
    for c in out.checks:
        print(f"  {'ok ' if c.met else 'NO '} {c.criterion}{'  -> ' + c.fix if c.fix else ''}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
