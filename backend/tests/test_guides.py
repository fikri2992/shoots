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
