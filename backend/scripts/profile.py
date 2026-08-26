"""Print the Tendency Profile over everything in the store.

    uv run python scripts/profile.py

Pure arithmetic on measurements already on disk: no model is called and
nothing is written. This is the report the Journey page renders and the Scout
reads when it chooses what to ask for next.
"""

import asyncio

from app.config import settings
from app.domain import tendency
from app.infra import repository as repo
from app.infra.store import FileStore


def bar(share: float, width: int = 22) -> str:
    filled = round(share * width)
    return "#" * filled + "." * (width - filled)


async def main() -> None:
    store = FileStore(settings.blob_root + "/store.json")
    for user in await repo.list_users(store):
        shots = await repo.list_shots(store, user.id)
        analyses = {
            analysis.shot_id: analysis for analysis in await repo.list_analyses(store, user.id)
        }
        rows = [(shot, analyses.get(shot.id)) for shot in shots]
        keepers = {shot.id for shot in shots if shot.kept_at}
        profile = tendency.build(rows, keepers)

        print(f"\n{user.id}: {profile.shots} shots, {profile.keepers} keepers")
        print(
            f"  scenes: {profile.dwell.scenes}, "
            f"{profile.dwell.per_scene:.1f} Shots a Scene, "
            f"longest {profile.dwell.longest}"
        )
        for dim in tendency.DIMENSIONS:
            p = profile.dimensions[dim.id]
            if not p.n:
                print(f"\n  {dim.label}: nothing readable ({p.unreadable} shots)")
                continue
            claim = "" if p.readable else "  (too few to claim anything)"
            print(f"\n  {dim.label}: explored {p.exploration:.2f}{claim}")
            for bucket in dim.buckets:
                count = p.counts.get(bucket, 0)
                marked = p.keepers.get(bucket, 0)
                mark = f"  {marked}/{p.readable_keepers} Keepers" if marked else ""
                print(f"    {bucket:<14} {bar(count / p.n)} {count:>3}{mark}")
            if p.unreadable:
                print(f"    {'unreadable':<14} {'':22} {p.unreadable:>3}")

        narrowest = profile.narrowest()
        print(f"\n  narrowest: {narrowest.dimension.label}" if narrowest else "\n  nothing narrow")
        if narrowest:
            print(f"    {narrowest.dominant}, {narrowest.dominant_share:.0%} of readable shots")
            if narrowest.never_used:
                print(f"    never: {', '.join(narrowest.never_used)}")
        print("\n  blind spots:")
        for spot in profile.blind_spots:
            print(f"    - {spot}")


if __name__ == "__main__":
    asyncio.run(main())
