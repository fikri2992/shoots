"""What the Coach remembers, and that the Scout respects it."""

from app.domain import scout as rules
from app.domain.entities import Constraints, TechniqueState, TechniqueStatus
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
    skills = {
        tid: TechniqueState(
            user_id="u", technique_id=tid, status=TechniqueStatus.OBSERVED, attempts=3
        )
        for tid in ("golden_hour", "deep_dof", "freeze_action", "backlight", "rule_of_thirds")
    }
    everything = [t.id for t in rules.rank(skills, [])]
    assert "long_exposure" in everything and "fill_flash" in everything
    without = [t.id for t in rules.rank(skills, [], missing_gear=["tripod", "flash"])]
    assert "long_exposure" not in without and "fill_flash" not in without
    assert "panning" in without  # no gear needed
