"""Move a store written before the vocabulary was locked (2026-08-25).

    uv run python scripts/migrate_vocabulary.py [--dry-run]

Stop the dev server first. Idempotent: running it twice changes nothing the
second time, and a store that is already current is left alone.

Three renames, and one of them is a real decision rather than a substitution.
`rusty` does not survive as a state, and what it becomes matters: a Technique
that decayed to `rusty` had *recurred* first, and decision 46 says time never
un-observes what the Evidence saw. So it becomes `recurring`, and whether it
is worth offering again is answered live by `technique_map.stale_ids` from
`last_observed`. Reading it as anything less would let the migration itself
demote work the photographer actually did.
"""

import asyncio
import sys

from app.config import settings
from app.infra.store import FileStore

#: Old Technique Map state → new. `practiced` and `attempted` were the same
#: claim with different adjectives; `solid` and `rusty` both mean it recurred.
STATUS = {
    "unexplored": "unobserved",
    "attempted": "observed",
    "practiced": "observed",
    "solid": "recurring",
    "rusty": "recurring",
}

EXPERIMENT_STATUS = {"passed": "completed"}


async def main(dry_run: bool) -> None:
    store = FileStore(settings.blob_root + "/store.json")
    raw = store._data

    changes: list[str] = []

    # Techniques: five graded states become three observed ones.
    for key, row in raw.get("skills", {}).items():
        old = row.get("status")
        if old in STATUS:
            row["status"] = STATUS[old]
            changes.append(f"skill {key}: {old} -> {row['status']}")
        if "last_practiced" in row:
            row["last_observed"] = row.pop("last_practiced")

    # Experiments: the collection and the outcome word.
    quests = raw.pop("quests", None)
    if quests is not None:
        raw.setdefault("experiments", {}).update(quests)
        changes.append(f"collection quests -> experiments ({len(quests)} rows)")
    for key, row in raw.get("experiments", {}).items():
        old = row.get("status")
        if old in EXPERIMENT_STATUS:
            row["status"] = EXPERIMENT_STATUS[old]
            changes.append(f"experiment {key}: {old} -> {row['status']}")

    # The id every Shot and event carried for the thing it answered.
    for collection in ("shots", "events"):
        for row in raw.get(collection, {}).values():
            if "quest_id" in row:
                row["experiment_id"] = row.pop("quest_id")

    # Findings, and the Keeper's positive-only shape.
    for row in raw.get("analyses", {}).values():
        if "faults" in row:
            row["findings"] = row.pop("faults")
            for finding in row["findings"]:
                if "fault_id" in finding:
                    finding["finding_id"] = finding.pop("fault_id")
    for row in raw.get("shots", {}).values():
        if "keeper" in row:
            # True became a mark with no date; False was never a rejection and
            # becomes silence, which is what it always meant (decision 45).
            was = row.pop("keeper")
            row["kept_at"] = row.get("kept_at") or (row.get("ingested_at") if was else None)

    for line in changes:
        print(" ", line)
    print(f"{len(changes)} changes")
    if dry_run:
        print("dry run: nothing written")
        return
    store._flush()
    print("written")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
