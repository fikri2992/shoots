"""What the Coach remembers, and that the Scout respects it."""

from app.domain import scout as rules
from app.domain.entities import Constraints
from app.services.coach import merge


def test_merge_keeps_known_gear_and_dedupes_notes():
    existing = Constraints(missing_gear=["tripod"], notes=["Shoots during lunch breaks"])
    merged = merge(
        existing,
        ["Tripod", "telescope", "flash"],
        ["shoots during lunch breaks.", "Walks everywhere; no car"],
    )
    assert merged.missing_gear == ["tripod", "flash"]
    assert merged.notes == ["Shoots during lunch breaks", "Walks everywhere; no car"]
    assert merged.updated_at is not None


def test_merge_caps_notes_newest_last():
    merged = merge(Constraints(), [], [f"note {i}" for i in range(12)])
    assert len(merged.notes) == 8 and merged.notes[-1] == "note 11"


def test_scout_skips_techniques_needing_missing_gear():
    preferred = ("long_exposure", "fill_flash", "panning")
    selected = rules.choose(preferred, [], missing_gear=["tripod", "flash"])
    assert selected is not None and selected.id == "panning"
