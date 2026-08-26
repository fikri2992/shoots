"""Pure Deconstruction page planning from already stored Evidence."""

import re
from collections import Counter

from app.domain import taxonomy
from app.domain.entities import (
    Analysis,
    DeconstructionPage,
    DeconstructionPageKind,
    Experiment,
    ExperimentType,
    ShootRecord,
    Shot,
)

PLAN_VERSION = "deconstruction-plan-1"
_CELL = re.compile(r"\b[A-H][1-6]\b", re.IGNORECASE)
_SCORE = re.compile(r"\bscore(?:d|s|ing)?\b", re.IGNORECASE)


def _plain(value: str) -> str:
    """Keep internal coordinates and score vocabulary out of export copy."""
    value = _CELL.sub("the marked area", value.strip())
    value = _SCORE.sub("read", value)
    return " ".join(value.split())


def cover_candidates(shots: list[Shot]) -> list[str]:
    return [shot.id for shot in shots if shot.kept_at is not None and shot.kind.value == "photo"]


def shoot_pages(
    record: ShootRecord,
    shots: list[Shot],
    analyses: list[Analysis],
    cover_shot_id: str,
) -> list[DeconstructionPage]:
    ordered = [shot.id for shot in shots if shot.id in record.shot_ids]
    pages = [
        DeconstructionPage(
            kind=DeconstructionPageKind.COVER,
            title="How I worked this Shoot",
            claim="A Keeper from this Shoot, chosen by me.",
            shot_ids=[cover_shot_id],
            evidence_refs=[f"shot:{cover_shot_id}:keeper"],
        ),
        DeconstructionPage(
            kind=DeconstructionPageKind.SHOOT_WORK,
            title=f"{record.receipt.shot_count} Shots · {record.receipt.scene_count} Scenes",
            claim=_plain(record.receipt.summary) or "This is the complete settled Shoot record.",
            shot_ids=ordered[:4],
            evidence_refs=[
                f"shoot:{record.shoot_id}:revision:{record.revision}",
                *[f"shot:{shot_id}" for shot_id in ordered[:4]],
            ],
        ),
    ]

    variation = next(
        (_plain(value) for value in record.receipt.varied if _plain(value)),
        "",
    ) or next(
        (_plain(value) for value in record.receipt.repeated if _plain(value)),
        "",
    )
    pages.append(
        DeconstructionPage(
            kind=DeconstructionPageKind.COMPOSITION,
            title="What I changed",
            claim=variation or "I changed the frame across the Shoot and kept the full sequence.",
            shot_ids=ordered[:4],
            evidence_refs=[f"shoot:{record.shoot_id}:receipt:{record.receipt.calc_version}"],
            visual_layer="annotated",
        )
    )

    technique_counts: Counter[str] = Counter()
    technique_shots: dict[str, list[str]] = {}
    for analysis in analyses:
        for evidence in analysis.techniques:
            if evidence.agreement < 2 or evidence.technique_id not in taxonomy.BY_ID:
                continue
            technique_counts[evidence.technique_id] += 1
            technique_shots.setdefault(evidence.technique_id, []).append(analysis.shot_id)
    if technique_counts:
        technique_id, count = technique_counts.most_common(1)[0]
        name = taxonomy.BY_ID[technique_id].name
        pages.append(
            DeconstructionPage(
                kind=DeconstructionPageKind.TECHNIQUE,
                title=name,
                claim=(
                    f"Two Analyst lenses corroborated {name} in {count} "
                    "of this Shoot's readable Shots."
                ),
                shot_ids=technique_shots[technique_id][:4],
                evidence_refs=[
                    *[
                        f"analysis:{shot_id}:technique:{technique_id}"
                        for shot_id in technique_shots[technique_id]
                    ],
                    f"technique:{technique_id}",
                ],
                visual_layer="annotated",
            )
        )

    pages.append(
        DeconstructionPage(
            kind=DeconstructionPageKind.RECORD,
            title="The record",
            claim=(
                f"{record.receipt.readable_shot_count} readable Shots, "
                f"{len(record.receipt.keeper_shot_ids)} marked Keepers, "
                f"{len(record.unreadable_shot_ids)} unreadable."
            ),
            shot_ids=[cover_shot_id],
            evidence_refs=[
                f"shoot:{record.shoot_id}:revision:{record.revision}",
                f"provenance:{record.provenance.calc_version}",
            ],
        )
    )
    return pages[:7]


def experiment_pages(
    experiment: Experiment,
    shots: list[Shot],
    cover_shot_id: str,
) -> list[DeconstructionPage]:
    ordered_ids = [
        shot_id
        for shot_id in [experiment.reference_shot_id, *experiment.result_shot_ids]
        if shot_id and any(shot.id == shot_id for shot in shots)
    ]
    pages = [
        DeconstructionPage(
            kind=DeconstructionPageKind.COVER,
            title=_plain(experiment.title),
            claim="A Keeper from this Experiment, chosen by me.",
            shot_ids=[cover_shot_id],
            evidence_refs=[f"shot:{cover_shot_id}:keeper"],
        ),
        DeconstructionPage(
            kind=(
                DeconstructionPageKind.EXPLORE
                if experiment.type is ExperimentType.EXPLORE
                else DeconstructionPageKind.REPRODUCE
            ),
            title="What I tried",
            claim=_plain(experiment.brief),
            shot_ids=ordered_ids[:4],
            evidence_refs=[f"experiment:{experiment.id}:brief"],
        ),
    ]
    if experiment.type is ExperimentType.EXPLORE:
        observed = len(experiment.variation_observations)
        covered = len({item.variation_id for item in experiment.variation_observations})
        pages.append(
            DeconstructionPage(
                kind=DeconstructionPageKind.EXPLORE,
                title="Variations observed",
                claim=(
                    f"{observed} result observations across {covered} Variations. "
                    "No result was graded."
                ),
                shot_ids=experiment.result_shot_ids[:4],
                evidence_refs=[
                    *[
                        f"experiment:{experiment.id}:observation:{item.shot_id}"
                        for item in experiment.variation_observations
                    ]
                ]
                or [f"experiment:{experiment.id}:results"],
            )
        )
    else:
        met = sum(verdict.criteria_met for verdict in experiment.verdicts)
        pages.append(
            DeconstructionPage(
                kind=DeconstructionPageKind.REPRODUCE,
                title="Declared check",
                claim=(
                    f"{met} of {len(experiment.verdicts)} recorded Verdicts met "
                    "the frozen Criteria."
                ),
                shot_ids=ordered_ids[:4],
                evidence_refs=[
                    f"experiment:{experiment.id}:criteria",
                    f"experiment:{experiment.id}:verdicts",
                ],
            )
        )
    if experiment.change is not None:
        pages.append(
            DeconstructionPage(
                kind=DeconstructionPageKind.CHANGE,
                title="What changed afterward",
                claim=_plain(experiment.change.outcome) or experiment.change.state.value,
                shot_ids=experiment.result_shot_ids[:4],
                evidence_refs=[f"experiment:{experiment.id}:change"],
            )
        )
    pages.append(
        DeconstructionPage(
            kind=DeconstructionPageKind.RECORD,
            title="The Experiment Record",
            claim=(
                f"{len(experiment.result_shot_ids)} explicit result Shots remain "
                f"attached to this {experiment.type.value} Experiment."
            ),
            shot_ids=[cover_shot_id],
            evidence_refs=[f"experiment:{experiment.id}:results"],
        )
    )
    return pages[:7]
