"""The rubric's arithmetic and the panel's vote, pure."""

import pytest

from app.domain import panel, rubric
from app.domain.panel import LensRead, Sighting


def test_overall_is_weighted_and_renormalised():
    assert (
        rubric.overall(
            {"impact": 10, "composition": 10, "lighting": 10, "technical": 10, "story": 10}
        )
        == 10
    )
    assert (
        rubric.overall({"impact": 8, "composition": 6, "lighting": 7, "technical": 5, "story": 6})
        == 7
    )
    # a missing element does not drag the mean down
    assert rubric.overall({"impact": 9, "composition": 9}) == 9
    assert rubric.overall({}) == 5
    assert rubric.overall({"impact": 40}) == 10
    assert rubric.band(8) == "merit" and rubric.band(5) == "below standard"
    assert "- 10: exceptional" in rubric.anchors_text()


def read(lens: str, *sightings: tuple[str, float], elements=None, observations=()) -> LensRead:
    return LensRead(
        lens=lens,
        sightings=[Sighting(technique_id=t, confidence=c) for t, c in sightings],
        elements=elements or {},
        observations=list(observations),
    )


def test_vote_rules():
    reads = [
        read("technician", ("panning", 0.9), ("shallow_dof", 0.8), ("golden_hour", 0.5)),
        read("composer", ("panning", 0.7), ("golden_hour", 0.6), ("leading_lines", 0.5)),
        read("storyteller", ("golden_hour", 0.45), ("monochrome", 0.3)),
    ]
    result = panel.aggregate(reads)
    by_id = {t.technique_id: t for t in result.techniques}
    assert by_id["panning"].agreement == 2
    assert by_id["golden_hour"].agreement == 3  # 0.45 is above the floor; three agree
    assert by_id["shallow_dof"].agreement == 1  # owner (technician) at 0.8 counts alone
    assert "leading_lines" not in by_id  # owner alone at 0.5: not enough
    assert "monochrome" not in by_id  # below the floor
    assert [t.technique_id for t in result.techniques][:2] == ["golden_hour", "panning"]
    assert ("composer", "leading_lines", 0.5) in result.dissent
    assert result.quorum == 3


def test_owner_map_and_overrides():
    assert panel.owner_of("panning") == "technician"
    assert panel.owner_of("rule_of_thirds") == "composer"
    assert panel.owner_of("single_accent") == "storyteller"
    assert panel.owner_of("slow_motion") == "technician"
    assert panel.owner_of("pan") == "composer"


def test_elements_average_only_over_owning_lenses_and_quorum_is_enforced():
    reads = [
        read("technician", elements={"technical": 6, "impact": 10}),
        read("composer", elements={"composition": 7, "lighting": 8}),
        read("storyteller", elements={"impact": 8, "story": 5}),
    ]
    result = panel.aggregate(reads)
    assert result.elements == {
        "impact": 8,
        "composition": 7,
        "lighting": 8,
        "technical": 6,
        "story": 5,
    }
    with pytest.raises(ValueError):
        panel.aggregate(reads[:1])


def test_observations_merge_dedupe_and_cap():
    reads = [
        read("technician", observations=["The rider at D4 is sharp.", "Fence streaked."]),
        read(
            "composer",
            observations=["the rider at D4 is sharp.", *[f"line {i}" for i in range(20)]],
        ),
    ]
    result = panel.aggregate(reads)
    assert result.observations[0] == "The rider at D4 is sharp."
    assert len(result.observations) == panel.MAX_OBSERVATIONS


def test_scrub_lens_votes_for_video_moves():
    reads = [
        read("technician", ("slow_motion", 0.9), elements={"technical": 6}),
        read("composer", ("pan", 0.55), elements={"composition": 6, "lighting": 6}),
        read("storyteller", elements={"impact": 5, "story": 5}),
        read("scrub", ("pan", 0.8)),
    ]
    result = panel.aggregate(reads)
    by_id = {t.technique_id: t for t in result.techniques}
    assert by_id["pan"].agreement == 2 and by_id["pan"].lenses == ["composer", "scrub"]
    assert result.quorum == 4 and "scrub" not in result.elements


# --- arithmetic outranks the panel -------------------------------------------


def test_a_measurement_that_rules_a_technique_out_drops_it_however_sure_the_lenses_were():
    """The bug this exists to close: the drift said the framing travelled, the
    lenses said tripod, and the evidence stood because the vote never read the
    measurement."""
    reads = [
        read("technician", ("static_tripod", 1.0)),
        read("composer", ("static_tripod", 1.0)),
        read("storyteller", ("static_tripod", 1.0)),
    ]
    result = panel.aggregate(reads, settled_against=frozenset({"static_tripod"}))
    assert result.techniques == []
    # It still travels as dissent: the feed shows what was claimed and lost.
    assert sorted(result.dissent) == [
        ("composer", "static_tripod", 1.0),
        ("storyteller", "static_tripod", 1.0),
        ("technician", "static_tripod", 1.0),
    ]


def test_the_veto_beats_a_trusted_owner():
    """An owner alone at >= 0.75 normally carries a technique on its own. The
    veto takes it anyway, and leaves everything it did not rule out alone."""
    reads = [read("composer", ("static_tripod", 0.95)), read("technician", ("panning", 0.9))]
    result = panel.aggregate(reads, settled_against=frozenset({"static_tripod"}))
    assert [t.technique_id for t in result.techniques] == ["panning"]
    assert result.dissent == [("composer", "static_tripod", 0.95)]


def test_one_lens_is_enough_when_the_measurement_agrees():
    """A pan measured at 2.42 frame widths does not need a second opinion."""
    reads = [
        read("composer", ("pan", 0.5)),
        read("technician", ("shallow_dof", 0.3)),
        read("storyteller",),
    ]
    result = panel.aggregate(reads, settled_for=frozenset({"pan"}))
    found = {t.technique_id: t for t in result.techniques}
    assert "pan" in found
    assert found["pan"].lenses == ["composer", panel.MEASURED]
    assert found["pan"].agreement == 2
    # Measured, not estimated: a proof does not get less certain because the
    # lens was only half sure. This is also what carries it past the skill
    # graph's corroboration bar.
    assert found["pan"].confidence == 1.0


def test_a_measurement_alone_invents_no_evidence():
    """Nothing saw it. A measurement with no reading behind it is a gap in the
    panel, not a sighting, so the vote stays quiet."""
    reads = [read("technician", ("shallow_dof", 0.9)), read("composer", ("leading_lines", 0.8))]
    result = panel.aggregate(reads, settled_for=frozenset({"pan"}))
    assert "pan" not in {t.technique_id for t in result.techniques}


def test_the_measurement_carries_no_cells_of_its_own():
    reads = [
        LensRead(lens="composer", sightings=[Sighting("pan", 0.6, cells=("C3", "D3"))]),
        LensRead(lens="technician", sightings=[]),
    ]
    result = panel.aggregate(reads, settled_for=frozenset({"pan"}))
    pan = next(t for t in result.techniques if t.technique_id == "pan")
    assert pan.cells == ["C3", "D3"]


def test_without_the_sets_nothing_changes():
    """Photos pass no measured sets at all; the vote must behave exactly as before."""
    reads = [
        read("technician", ("panning", 0.9), ("shallow_dof", 0.8)),
        read("composer", ("panning", 0.7), ("leading_lines", 0.5)),
        read("storyteller", ("monochrome", 0.3)),
    ]
    plain = panel.aggregate(reads)
    empty = panel.aggregate(reads, settled_for=frozenset(), settled_against=frozenset())
    assert [(t.technique_id, t.agreement, t.confidence) for t in plain.techniques] == [
        (t.technique_id, t.agreement, t.confidence) for t in empty.techniques
    ]
