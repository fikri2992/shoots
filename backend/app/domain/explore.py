"""Pure corrected-Explore Variations and structured observations."""

from app.domain import technique_map
from app.domain.entities import Analysis, Variation, VariationObservation
from app.domain.taxonomy import Technique

VARIATION_VERSION = "explore-variations-1"


def variations_for(technique: Technique) -> list[Variation]:
    name = technique.name
    return [
        Variation(
            id=f"{technique.id}:clear",
            title=f"Let {name} lead",
            instruction=f"Make {name} the first thing the eye notices.",
        ),
        Variation(
            id=f"{technique.id}:restrained",
            title=f"Use {name} quietly",
            instruction=f"Let {name} support the Shot without taking over.",
        ),
        Variation(
            id=f"{technique.id}:invert",
            title="Try the opposite",
            instruction=(
                f"Keep the subject or Scene similar, but deliberately avoid {name}. "
                "See what changes."
            ),
            inversion=True,
        ),
    ]


def observe(
    analysis: Analysis,
    variation_id: str,
) -> VariationObservation:
    evidence = [
        item for item in analysis.techniques if item.confidence >= technique_map.MIN_CONFIDENCE
    ]
    return VariationObservation(
        variation_id=variation_id,
        shot_id=analysis.shot_id,
        technique_ids=sorted({item.technique_id for item in evidence}),
        corroborated_technique_ids=sorted(
            {item.technique_id for item in evidence if technique_map.corroborated(item)}
        ),
        guide=analysis.composition.guide,
        finding_ids=sorted({item.finding_id for item in analysis.findings}),
        abstained=analysis.abstained,
        model=analysis.model,
        prompt_version=analysis.prompt_version,
        observed_at=analysis.created_at,
    )
