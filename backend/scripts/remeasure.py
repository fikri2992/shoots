"""Measure colour, tone and camera movement on shots ingested before we did.

    uv run python scripts/remeasure.py [shot_id ...]

Stop the dev server first (two processes on one store.json lose writes).

Only the measurement runs. Nothing is re-analysed, no model is called and no
verdict moves: the frame is read back out of its stored ``original`` blob,
``imaging/tone.py`` and ``imaging/motion.py`` measure it, and the two fields
are written onto the Shot. Every existing shot predates the measurement and
would otherwise show an empty readout and give the panel nothing to cite.

To have the lenses actually use the new facts, follow with:

    uv run python scripts/reanalyse.py
"""

import asyncio
import sys

from app.config import settings
from app.domain import motion as motion_rules
from app.domain import tone as tone_rules
from app.domain.entities import ShotKind
from app.imaging import canvas, motion, video
from app.imaging.tone import measure as measure_tone
from app.infra import repository as repo
from app.infra.storage import ORIGINAL
from app.infra.store import FileStore
from app.services.ingest import sample_times


async def main(shot_ids: list[str]) -> None:
    store = FileStore(settings.blob_root + "/store.json")
    from app.infra.storage import LocalBlobStore

    blobs = LocalBlobStore()

    shots = []
    for user in await repo.list_users(store):
        shots += await repo.list_shots(store, user.id, limit=10_000)
    if shot_ids:
        shots = [s for s in shots if s.id in set(shot_ids)]

    done = skipped = 0
    for shot in shots:
        path = shot.blobs.get(ORIGINAL)
        if not path:
            skipped += 1
            continue
        try:
            data = await blobs.read(path)
            if shot.kind is ShotKind.VIDEO:
                # The first sampled frame, as ingest measures it: the contact
                # sheet's padding would report the sheet's palette, not the
                # photographer's.
                info = await video.probe(data)
                first = sample_times(info.duration, [], settings.video_min_frames, 1)[0]
                shot.tone = measure_tone(canvas.from_bytes(await video.frame_at(data, first)))
                shot.motion = await motion.measure(data)
            else:
                shot.tone = measure_tone(canvas.load_bytes(data))
        except Exception as error:  # noqa: BLE001 — one bad file must not stop the sweep
            print(f"  {shot.id}: {type(error).__name__}: {error}")
            skipped += 1
            continue

        await repo.put_shot(store, shot)
        done += 1
        headline = tone_rules.describe(shot.tone, shot.exif)
        move = motion_rules.describe(shot.motion)
        print(f"{shot.filename}")
        for line in headline[:2] + move[:1]:
            print(f"    {line}")

    print(f"\nmeasured {done} shots, skipped {skipped}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
