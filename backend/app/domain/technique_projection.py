"""Rebuild the Technique Map from authoritative evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime

from app.domain import taxonomy
from app.domain import technique_map as rules
from app.domain.entities import (
    Analysis,
    Experiment,
    ExperimentType,
    TechniqueEvidence,
    TechniqueState,
)

PROJECTION_VERSION = "technique-map-3"


@dataclass(frozen=True)
class ShotFact:
    observed_at: datetime
    kept: bool = False
    scene_id: str = ""
    shoot_id: str = ""


@dataclass(frozen=True)
class ProjectionInputs:
    user_id: str
    analyses: tuple[Analysis, ...] = ()
    shots: dict[str, ShotFact] = field(default_factory=dict)
    experiments: tuple[Experiment, ...] = ()
    abstained_by_experiment: dict[str, frozenset[str]] = field(default_factory=dict)
    existing_technique_ids: frozenset[str] = frozenset()


def build(inputs: ProjectionInputs) -> dict[str, TechniqueState]:
    """Return the complete current projection, including honest retractions."""
    evidence_by_technique: dict[str, dict[str, tuple[Analysis, TechniqueEvidence]]] = {}
    for analysis in inputs.analyses:
        if analysis.shot_id not in inputs.shots:
            continue
        for evidence in analysis.techniques:
            if (
                evidence.technique_id not in taxonomy.BY_ID
                or evidence.confidence < rules.MIN_CONFIDENCE
            ):
                continue
            by_shot = evidence_by_technique.setdefault(evidence.technique_id, {})
            previous = by_shot.get(analysis.shot_id)
            if previous is None or _evidence_strength(evidence) > _evidence_strength(previous[1]):
                by_shot[analysis.shot_id] = (analysis, evidence)

    experiments_by_technique: dict[str, list[Experiment]] = {}
    for experiment in inputs.experiments:
        if experiment.type is ExperimentType.REPRODUCE:
            experiments_by_technique.setdefault(experiment.technique_id, []).append(experiment)

    technique_ids = (
        set(inputs.existing_technique_ids)
        | set(evidence_by_technique)
        | set(experiments_by_technique)
    )
    return {
        technique_id: _state(
            inputs,
            technique_id,
            list(evidence_by_technique.get(technique_id, {}).values()),
            experiments_by_technique.get(technique_id, []),
        )
        for technique_id in sorted(technique_ids)
        if technique_id in taxonomy.BY_ID
    }


def _evidence_strength(evidence: TechniqueEvidence) -> tuple[bool, float, int]:
    """Choose one conservative Technique sighting when a reader repeats a label."""
    return (rules.corroborated(evidence), evidence.confidence, evidence.agreement)


def _state(
    inputs: ProjectionInputs,
    technique_id: str,
    evidence_rows: list[tuple[Analysis, TechniqueEvidence]],
    experiments: list[Experiment],
) -> TechniqueState:
    ordered = sorted(
        evidence_rows,
        key=lambda row: (
            inputs.shots.get(row[0].shot_id, ShotFact(row[0].created_at)).observed_at,
            row[0].shot_id,
        ),
    )
    observed_ids = [analysis.shot_id for analysis, _ in ordered]
    corroborated = [
        (analysis, evidence) for analysis, evidence in ordered if rules.corroborated(evidence)
    ]
    corroborated_ids = {analysis.shot_id for analysis, _ in corroborated}
    scenes = {
        fact.scene_id
        for shot_id in corroborated_ids
        if (fact := inputs.shots.get(shot_id)) is not None and fact.scene_id
    }
    shoots = {
        fact.shoot_id
        for shot_id in corroborated_ids
        if (fact := inputs.shots.get(shot_id)) is not None and fact.shoot_id
    }
    result_ids = {shot_id for experiment in experiments for shot_id in experiment.result_shot_ids}
    met_ids = {
        verdict.shot_id
        for experiment in experiments
        for verdict in experiment.verdicts
        if verdict.criteria_met
    }
    abstained_ids = {
        shot_id
        for experiment in experiments
        for shot_id in inputs.abstained_by_experiment.get(experiment.id, frozenset())
    }
    kept_ids = {
        shot_id
        for shot_id in corroborated_ids
        if (fact := inputs.shots.get(shot_id)) is not None and fact.kept
    }
    last_observed = max(
        (
            inputs.shots.get(analysis.shot_id, ShotFact(analysis.created_at)).observed_at
            for analysis, _ in ordered
        ),
        default=None,
    )
    state = TechniqueState(
        user_id=inputs.user_id,
        technique_id=technique_id,
        attempts=len(observed_ids),
        corroborated=len(corroborated_ids),
        best_confidence=max((evidence.confidence for _, evidence in ordered), default=0.0),
        last_observed=last_observed,
        shot_ids=observed_ids[-rules.SHOT_MEMORY :],
        sightings=len(observed_ids),
        corroborated_shots=len(corroborated_ids),
        distinct_scenes=len(scenes),
        distinct_shoots=len(shoots),
        reproduce_attempts=len(result_ids),
        criteria_met_results=len(met_ids),
        abstentions=len(abstained_ids),
        positive_keeper_shots=len(kept_ids),
        supported_condition_coverage={},
        projection_version=PROJECTION_VERSION,
    )
    state.input_digest = _digest(inputs, technique_id, ordered, experiments)
    return rules.normalise_state(state)


def _digest(
    inputs: ProjectionInputs,
    technique_id: str,
    evidence_rows: list[tuple[Analysis, TechniqueEvidence]],
    experiments: list[Experiment],
) -> str:
    payload = {
        "version": PROJECTION_VERSION,
        "technique_id": technique_id,
        "evidence": [
            {
                "shot_id": analysis.shot_id,
                "model": analysis.model,
                "prompt_version": analysis.prompt_version,
                "confidence": evidence.confidence,
                "agreement": evidence.agreement,
                "kept": inputs.shots.get(
                    analysis.shot_id,
                    ShotFact(analysis.created_at),
                ).kept,
                "scene_id": inputs.shots.get(
                    analysis.shot_id,
                    ShotFact(analysis.created_at),
                ).scene_id,
                "shoot_id": inputs.shots.get(
                    analysis.shot_id,
                    ShotFact(analysis.created_at),
                ).shoot_id,
            }
            for analysis, evidence in evidence_rows
        ],
        "experiments": [
            {
                "id": experiment.id,
                "results": sorted(set(experiment.result_shot_ids)),
                "met": sorted(
                    verdict.shot_id for verdict in experiment.verdicts if verdict.criteria_met
                ),
                "abstained": sorted(inputs.abstained_by_experiment.get(experiment.id, frozenset())),
            }
            for experiment in sorted(experiments, key=lambda item: item.id)
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]
