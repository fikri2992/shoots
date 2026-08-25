"""Issue a experiment with the real model against the local dev store.

    uv run python scripts/check_scout.py [user_id]

Reads backend/.blobs/store.json (the FileStore the dev server writes), so it
sees the real skill graph built from your analysed shots, runs Scout
(grounded research + structured write) and prints the experiment. Writes it back
to the same store, so the dashboard shows it.
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
from app.services import scout
from app.services.context import Context


async def main(user_id: str | None) -> None:
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
    user = next((u for u in users if u.id == user_id), users[0])
    skills = await repo.list_skills(store, user.id)
    print(f"user {user.email}: {len(skills)} techniques attempted")
    for s in sorted(skills, key=lambda s: s.technique_id):
        print(
            f"  {s.technique_id:22} {s.status.value:10} attempts={s.attempts} best={s.best_score}"
        )

    experiment = await scout.issue(ctx, user.id, force=True)
    if experiment is None:
        print("nothing issued (open experiment exists or nothing to issue)")
        return
    print(f"\n=== {experiment.title}  [{experiment.technique_id}]")
    print(f"why now: {experiment.why_now}")
    print(f"brief:\n{experiment.brief}")
    print("criteria:")
    print(f"  exif: {experiment.criteria.exif.model_dump(exclude_none=True)}")
    print(f"  vision: {experiment.criteria.vision}")
    for t in experiment.criteria.text:
        print(f"  - {t}")
    print("references:")
    for r in experiment.references:
        print(f"  - {r.title}  {r.url}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
