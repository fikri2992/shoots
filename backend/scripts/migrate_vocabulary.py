"""Move a store written before the vocabulary was locked (2026-08-25).

    uv run python scripts/migrate_vocabulary.py [--dry-run]

Stop the dev server first. Idempotent: running it twice changes nothing the
second time, and a store that is already current is left alone.

Most of it is renaming, but two entries are real decisions rather than
substitutions, and both come out the same way: where the old shape cannot be
read honestly, the migration keeps the evidence and drops the verdict.

Old `solid` and `rusty` labels were partly score-derived. The current Map does
not preserve their grade as recurrence: attempts and corroborated sightings
are the authority. A row becomes `recurring` only when its own current counts
meet that rule; otherwise it remains honestly `observed`.

`TendencyGrade.moved` becomes a `Baseline` with no `Change` at all, for the
reason given in `_experiment_record`: a two-state answer cannot say "I cannot
tell", so carrying it across would preserve conclusions the current rules would
not draw.
"""

import asyncio
import sys

from app.config import settings
from app.domain import technique_map
from app.infra.store import FileStore

#: Old Technique Map state → a provisional current noun. Counts below decide
#: whether any observed row has enough corroboration to be recurring.
STATUS = {
    "unexplored": "unobserved",
    "attempted": "observed",
    "practiced": "observed",
    "solid": "observed",
    "rusty": "observed",
}

EXPERIMENT_STATUS = {"passed": "completed"}


async def main(dry_run: bool) -> None:
    store = FileStore(settings.blob_root + "/store.json")
    raw = store._data

    #: Every rename that touched anything, so ``--dry-run`` can be trusted.
    #: Four of these used to run silently and report nothing, which meant a
    #: store still holding `faults` or `quest_id` printed "0 changes" and an
    #: operator doing the documented safe thing concluded it was current. The
    #: models ignore unknown keys rather than failing, so the next load would
    #: have dropped every stored Finding without an error anywhere.
    changes: list[str] = []

    # Techniques: five graded states become three observed ones.
    for key, row in raw.get("skills", {}).items():
        old = row.get("status")
        if old in STATUS:
            row["status"] = STATUS[old]
            changes.append(f"Technique state {key}: {old} -> {row['status']}")
        attempts = int(row.get("attempts") or 0)
        corroborated = int(row.get("corroborated") or 0)
        expected = (
            "recurring"
            if attempts >= technique_map.RECURRING_MIN_ATTEMPTS
            and corroborated >= technique_map.RECURRING_MIN_CORROBORATED
            else "observed"
            if attempts > 0
            else "unobserved"
        )
        if row.get("status") != expected:
            changes.append(
                f"Technique state {key}: {row.get('status')} -> {expected} from Evidence counts"
            )
            row["status"] = expected
        if "last_practiced" in row:
            row["last_observed"] = row.pop("last_practiced")
            changes.append(f"Technique state {key}: last_practiced -> last_observed")
        for field in ("best_score", "last_score"):
            if field in row:
                row.pop(field)
                changes.append(f"Technique state {key}: removed {field}")

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
        changes += _experiment_record(key, row)

    # The id every Shot and event carried for the thing it answered.
    for collection in ("shots", "events"):
        for key, row in raw.get(collection, {}).items():
            if "quest_id" in row:
                row["experiment_id"] = row.pop("quest_id")
                changes.append(f"{collection} {key}: quest_id -> experiment_id")

    # Findings, and the Keeper's positive-only shape.
    for key, row in raw.get("analyses", {}).items():
        if "faults" in row:
            row["findings"] = row.pop("faults")
            for finding in row["findings"]:
                if "fault_id" in finding:
                    finding["finding_id"] = finding.pop("fault_id")
            changes.append(f"analysis {key}: faults -> findings ({len(row['findings'])})")
        for field in ("score", "elements"):
            if field in row:
                row.pop(field)
                changes.append(f"analysis {key}: removed {field}")
    for key, row in raw.get("shots", {}).items():
        if "keeper" in row:
            # True became a mark with no date; False was never a rejection and
            # becomes silence, which is what it always meant (decision 45).
            was = row.pop("keeper")
            row["kept_at"] = row.get("kept_at") or (row.get("ingested_at") if was else None)
            changes.append(f"shot {key}: keeper={was} -> kept_at")

    # The Journey's own graded word.
    for key, row in raw.get("journey", {}).items():
        if "became_solid" in row:
            row["became_recurring"] = row.pop("became_solid")
            changes.append(f"journey {key}: became_solid -> became_recurring")

    for line in changes:
        print(" ", line)
    print(f"{len(changes)} changes")
    if dry_run:
        print("dry run: nothing written")
        return
    store._flush()
    print("written")


def _experiment_record(key: str, row: dict) -> list[str]:
    """One Experiment becomes an Experiment Record: a type, a frozen Baseline,
    and a Change with three states instead of a boolean.

    The old ``moved`` flag is deliberately *not* carried across. It was decided
    before a minimum sample existed, so a `false` might mean "the distribution
    held over forty frames" or "one frame arrived and it was the usual kind" -
    and the second is `insufficient evidence`, not `unchanged`. Re-checking is
    pure arithmetic over counts that are still on disk, so the honest move is
    to keep the Baseline, drop the verdict, and let the next tick answer it
    under the rules that are actually in force.
    """
    changes: list[str] = []
    if "type" not in row:
        row["type"] = "explore"
        changes.append(f"experiment {key}: type -> explore")
    # A Verdict answers the Criteria the photographer declared in advance. A
    # person passes or fails; a declared check is met or is not (decision 46).
    for verdict in row.get("verdicts", []):
        if "passed" in verdict:
            verdict["criteria_met"] = verdict.pop("passed")
            changes.append(f"experiment {key}: verdict passed -> criteria_met")
    mark = row.pop("tendency", None)
    if mark is None:
        return changes
    row["baseline"] = {
        "source": mark.get("source", ""),
        "citation": mark.get("citation", ""),
        "at_issue": mark.get("at_issue", {}),
        "calc_version": mark.get("calc_version", ""),
        # No Shot ids were kept back then, and inventing a sample size would
        # make every later "shots since" figure wrong. Left empty on purpose:
        # the Change reports `unrecorded sample` and says so.
        "provenance": {},
        "frozen_at": row.get("issued_at"),
    }
    changes.append(f"experiment {key}: tendency -> baseline (change re-checked)")
    return changes


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
