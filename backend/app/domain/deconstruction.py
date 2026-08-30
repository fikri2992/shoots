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

PLAN_VERSION = "deconstruction-story-plan-2"
_CELL = re.compile(r"\b[A-H][1-6]\b", re.IGNORECASE)
_SCORE = re.compile(r"\bscore(?:d|s|ing)?\b", re.IGNORECASE)
_STORY_REWRITES = (
    (re.compile(r"\bShoot Record\b", re.IGNORECASE), "Shoot story"),
    (re.compile(r"\bExperiment Record\b", re.IGNORECASE), "Experiment story"),
    (re.compile(r"\bKeepers\b", re.IGNORECASE), "marked Shots"),
    (re.compile(r"\bKeeper\b", re.IGNORECASE), "marked Shot"),
    (re.compile(r"\bCriteria\b", re.IGNORECASE), "check"),
    (re.compile(r"\bVerdicts\b", re.IGNORECASE), "results"),
    (re.compile(r"\bVerdict\b", re.IGNORECASE), "result"),
    (re.compile(r"\bEvidence\b", re.IGNORECASE), "what the Shots show"),
)


def _plain(value: str) -> str:
    """Keep internal coordinates and score vocabulary out of export copy."""
    value = _CELL.sub("the marked area", value.strip())
    value = _SCORE.sub("read", value)
    return " ".join(value.split())


def _story(value: str) -> str:
    value = _plain(value)
    for pattern, replacement in _STORY_REWRITES:
        value = pattern.sub(replacement, value)
    return value


def _count(value: int, singular: str) -> str:
    return f"{value} {singular}{'' if value == 1 else 's'}"


def cover_candidates(shots: list[Shot]) -> list[str]:
    return [shot.id for shot in shots if shot.kept_at is not None and shot.kind.value == "photo"]


def shoot_pages(
    record: ShootRecord,
    shots: list[Shot],
    analyses: list[Analysis],
    cover_shot_id: str,
) -> list[DeconstructionPage]:
    available = {shot.id for shot in shots}
    ordered = [shot_id for shot_id in record.shot_ids if shot_id in available]
    opening_claim = next(
        (_story(value) for value in record.receipt.repeated if _story(value)),
        "",
    ) or _story(record.receipt.summary)
    pages = [
        DeconstructionPage(
            kind=DeconstructionPageKind.COVER,
            title="The opening",
            claim=opening_claim or "This Shot opens the story.",
            shot_ids=[cover_shot_id],
            evidence_refs=[
                f"shot:{cover_shot_id}:keeper",
                f"shoot:{record.shoot_id}:receipt:{record.receipt.calc_version}",
            ],
        ),
        DeconstructionPage(
            kind=DeconstructionPageKind.SHOOT_WORK,
            title="The setting",
            claim=(
                f"I made {_count(record.receipt.shot_count, 'Shot')} across "
                f"{_count(record.receipt.scene_count, 'Scene')}."
            ),
            shot_ids=ordered[:4],
            evidence_refs=[
                f"shoot:{record.shoot_id}:revision:{record.revision}",
                *[f"shot:{shot_id}" for shot_id in ordered[:4]],
            ],
        ),
    ]

    variation = next(
        (_story(value) for value in record.receipt.varied if _story(value)),
        "",
    )
    repeated = next(
        (_story(value) for value in record.receipt.repeated if _story(value)),
        "",
    )
    middle_title = "The turn" if variation else "What stayed" if repeated else "The sequence"
    middle_claim = variation or repeated or "The Shots stay in the order I made them."
    pages.append(
        DeconstructionPage(
            kind=DeconstructionPageKind.COMPOSITION,
            title=middle_title,
            claim=middle_claim,
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
                title="The thread",
                claim=f"{name} returns in {_count(count, 'Shot')}.",
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
            title="The ending",
            claim=_shoot_ending(record),
            shot_ids=[ordered[-1] if ordered else cover_shot_id],
            evidence_refs=[
                f"shoot:{record.shoot_id}:revision:{record.revision}",
                f"provenance:{record.provenance.calc_version}",
            ],
        )
    )
    return pages[:7]


def shoot_caption(record: ShootRecord) -> str:
    opening = _story(record.receipt.summary) or (
        f"{_count(record.receipt.shot_count, 'Shot')} across "
        f"{_count(record.receipt.scene_count, 'Scene')}."
    )
    return f"{opening} I chose this cover. Shoots kept the order I shot."


def _shoot_ending(record: ShootRecord) -> str:
    unreadable = len(record.unreadable_shot_ids)
    if unreadable:
        readable = record.receipt.readable_shot_count
        return (
            f"{_count(readable, 'Shot')} carry the story. "
            f"{_count(unreadable, 'other')} remain in the Shoot, but Shoots could not read them."
        )
    return f"All {_count(record.receipt.shot_count, 'Shot')} stay in the order I made them."


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
            title="The opening",
            claim=_story(experiment.title) or "This Shot opens the story.",
            shot_ids=[cover_shot_id],
            evidence_refs=[
                f"shot:{cover_shot_id}:keeper",
                f"experiment:{experiment.id}:title",
            ],
        ),
        DeconstructionPage(
            kind=(
                DeconstructionPageKind.EXPLORE
                if experiment.type is ExperimentType.EXPLORE
                else DeconstructionPageKind.REPRODUCE
            ),
            title="The idea",
            claim=_story(experiment.brief),
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
                title="The attempts",
                claim=(
                    f"I tried the idea {_count(covered, 'way')} across "
                    f"{_count(observed, 'result Shot')}. None is ranked."
                    if observed
                    else "These result Shots keep the attempts together. None is ranked."
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
                title="What returned",
                claim=(
                    f"{met} of {len(experiment.verdicts)} checked Shots matched what I set "
                    "before shooting."
                    if experiment.verdicts
                    else "These result Shots could not answer the check I set before shooting."
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
                title="What came next",
                claim=_story(experiment.change.outcome) or experiment.change.state.value,
                shot_ids=experiment.result_shot_ids[:4],
                evidence_refs=[f"experiment:{experiment.id}:change"],
            )
        )
    pages.append(
        DeconstructionPage(
            kind=DeconstructionPageKind.RECORD,
            title="The ending",
            claim=(
                f"I ended with {_count(len(experiment.result_shot_ids), 'result Shot')} "
                "from this idea."
            ),
            shot_ids=[
                experiment.result_shot_ids[-1] if experiment.result_shot_ids else cover_shot_id
            ],
            evidence_refs=[f"experiment:{experiment.id}:results"],
        )
    )
    return pages[:7]


def experiment_caption(experiment: Experiment) -> str:
    result_count = len(experiment.result_shot_ids)
    ending = (
        "No winner, just the versions I tried."
        if experiment.type is ExperimentType.EXPLORE
        else "I set the check before shooting. These pages show what matched."
    )
    return (
        f'I tried "{_story(experiment.title)}" in {_count(result_count, "result Shot")}. {ending}'
    )
