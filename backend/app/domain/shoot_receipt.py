"""Deterministic synthesis for one immutable Shoot revision."""

from collections.abc import Sequence

from app.domain import taxonomy, tendency
from app.domain.entities import (
    Analysis,
    EvidenceAuthority,
    ShootDimensionFigure,
    ShootReceipt,
    ShootTechniqueFigure,
    Shot,
)

CALC_VERSION = f"shoot-receipt-1+{tendency.CALC_VERSION}"
VARIED_AT = 0.45
REPEATED_SHARE = 0.75


def synthesize(
    *,
    shot_ids: Sequence[str],
    scene_shot_ids: Sequence[Sequence[str]],
    shots: Sequence[Shot],
    analyses: Sequence[Analysis],
    profile: tendency.Profile,
    unreadable_shot_ids: Sequence[str],
) -> ShootReceipt:
    """Account for a frozen Shoot without grading it or inferring Intent."""
    exact_ids = list(shot_ids)
    shot_by_id = {shot.id: shot for shot in shots}
    analysis_by_id = {analysis.shot_id: analysis for analysis in analyses}
    readable_ids = [shot_id for shot_id in exact_ids if shot_id in analysis_by_id]
    terminal_ids = [shot_id for shot_id in exact_ids if shot_id in unreadable_shot_ids]
    keeper_ids = [
        shot_id
        for shot_id in exact_ids
        if shot_id in shot_by_id and shot_by_id[shot_id].kept_at is not None
    ]

    dimensions: list[ShootDimensionFigure] = []
    repeated: list[str] = []
    varied: list[str] = []
    blind_spots: list[str] = []
    for dimension in tendency.DIMENSIONS:
        dimension_profile = profile.dimensions[dimension.id]
        authority = (
            EvidenceAuthority.MODEL_READ
            if dimension.source == "model read"
            else EvidenceAuthority.MEASURED
        )
        counts = {
            bucket: dimension_profile.counts[bucket]
            for bucket in dimension.buckets
            if dimension_profile.counts.get(bucket)
        }
        missing = len(exact_ids) - dimension_profile.n
        blind_spot = ""
        if missing:
            reason = dimension.blind or "not available on every member Shot"
            blind_spot = (
                f"{dimension.label.capitalize()} is still unclear. "
                f"{missing} of {len(exact_ids)} Shots have no reading. "
                f"{reason[:1].upper()}{reason[1:]}."
            )
            blind_spots.append(blind_spot)
        figure = ShootDimensionFigure(
            dimension_id=dimension.id,
            label=dimension.label,
            authority=authority,
            counts=counts,
            readable_shots=dimension_profile.n,
            unreadable_shots=missing,
            dominant=dimension_profile.dominant,
            dominant_count=dimension_profile.counts.get(dimension_profile.dominant, 0),
            exploration=round(dimension_profile.exploration, 3),
            blind_spot=blind_spot,
        )
        dimensions.append(figure)
        if dimension_profile.n < 2:
            continue
        authority_copy = (
            "Shoots saw this in the images"
            if authority is EvidenceAuthority.MODEL_READ
            else "Shoots read this from the files"
        )
        if len(counts) > 1 and dimension_profile.exploration >= VARIED_AT:
            buckets = ", ".join(f"{count} {name}" for name, count in counts.items())
            varied.append(
                f"{dimension.label.capitalize()} moved around: {buckets}. {authority_copy}."
            )
        elif figure.dominant_count >= 2 and dimension_profile.dominant_share >= REPEATED_SHARE:
            repeated.append(
                f"{figure.dominant.capitalize()} kept returning in {figure.dominant_count} of "
                f"{dimension_profile.n} Shots for {dimension.label}. {authority_copy}."
            )

    techniques = _technique_figures(exact_ids, analysis_by_id)
    for technique in techniques:
        if len(technique.corroborated_shot_ids) < 2:
            continue
        repeated.append(
            f"{technique.name} kept returning in "
            f"{len(technique.corroborated_shot_ids)} Shots. Shoots saw this in the images."
        )

    summary = f"You made {len(exact_ids)} Shots across {len(scene_shot_ids)} Scenes"
    if terminal_ids:
        summary += f". Shoots could not read {len(terminal_ids)} of them"
    summary += "."
    return ShootReceipt(
        calc_version=CALC_VERSION,
        summary=summary,
        shot_count=len(exact_ids),
        scene_count=len(scene_shot_ids),
        shots_per_scene=[len(ids) for ids in scene_shot_ids],
        readable_shot_count=len(readable_ids),
        unreadable_shot_ids=terminal_ids,
        keeper_shot_ids=keeper_ids,
        repeated=repeated[:4],
        varied=varied[:3],
        blind_spots=blind_spots,
        dimensions=dimensions,
        techniques=techniques,
    )


def _technique_figures(
    exact_ids: Sequence[str], analysis_by_id: dict[str, Analysis]
) -> list[ShootTechniqueFigure]:
    observed: dict[str, list[str]] = {}
    corroborated: dict[str, list[str]] = {}
    for shot_id in exact_ids:
        analysis = analysis_by_id.get(shot_id)
        if analysis is None:
            continue
        for evidence in analysis.techniques:
            if evidence.technique_id not in taxonomy.BY_ID:
                continue
            observed.setdefault(evidence.technique_id, []).append(shot_id)
            if evidence.agreement >= 2:
                corroborated.setdefault(evidence.technique_id, []).append(shot_id)
    return [
        ShootTechniqueFigure(
            technique_id=technique_id,
            name=taxonomy.BY_ID[technique_id].name,
            observed_shot_ids=shot_ids,
            corroborated_shot_ids=corroborated.get(technique_id, []),
        )
        for technique_id, shot_ids in sorted(
            observed.items(),
            key=lambda item: (
                -len(corroborated.get(item[0], [])),
                -len(item[1]),
                item[0],
            ),
        )
    ]
