"""Which guide a photographer is shown over their own frame."""

from app.domain import guides
from app.domain.entities import TechniqueEvidence


def evidence(*pairs: tuple[str, float]) -> list[TechniqueEvidence]:
    return [TechniqueEvidence(technique_id=t, confidence=c) for t, c in pairs]


def test_the_strongest_spatial_technique_picks_the_guide():
    assert guides.choose(evidence(("centre_composition", 0.9), ("rule_of_thirds", 0.5))) == "centre"
    assert guides.choose(evidence(("rule_of_thirds", 0.9), ("symmetry", 0.5))) == "thirds"
    assert guides.choose(evidence(("leading_lines", 0.8))) == "diagonals"
    assert guides.choose(evidence(("fill_the_frame", 0.8))) == "fill"


def test_techniques_with_no_geometry_do_not_vote():
    # Light, colour and lens techniques have nothing to draw a guide from.
    assert guides.choose(evidence(("golden_hour", 0.95), ("warm_cool", 0.9))) == guides.FALLBACK
    assert guides.choose([]) == guides.FALLBACK


def test_every_mapped_guide_is_one_the_renderers_know():
    assert set(guides.BY_TECHNIQUE.values()) <= set(guides.GUIDES)
    assert guides.FALLBACK in guides.GUIDES


def test_the_subject_picks_between_the_two_placement_grids():
    """Thirds and phi are 0.049 apart. No lens can see that, so the choice is
    measured from the point the Composer gave."""
    thirds = evidence(("rule_of_thirds", 0.9))
    assert guides.choose(thirds, subject_x=0.34, subject_y=0.5) == "thirds"
    assert guides.choose(thirds, subject_x=0.38, subject_y=0.5) == "phi"
    assert guides.choose(thirds, subject_x=0.61, subject_y=0.5) == "phi"
    assert guides.choose(thirds, subject_x=0.67, subject_y=0.5) == "thirds"


def test_without_a_point_the_technique_still_decides_alone():
    assert guides.choose(evidence(("rule_of_thirds", 0.9))) == "thirds"
    assert guides.choose([], subject_x=None, subject_y=None) == guides.FALLBACK


def test_only_a_placement_guide_is_refined():
    """A centred or diagonal frame is not a placement question; redrawing it on
    a phi grid would answer something nobody asked."""
    for guide in ("centre", "diagonals", "fill", "none"):
        assert guides.refine(guide, 0.382, 0.382) == guide


def test_phi_is_reachable_at_all():
    """It was not: nothing in BY_TECHNIQUE ever returned it, so the grid the
    renderers draw and test could never be chosen for anyone."""
    assert guides.PHI not in set(guides.BY_TECHNIQUE.values())
    assert guides.choose(evidence(("rule_of_thirds", 0.9)), 0.382, 0.5) == guides.PHI
