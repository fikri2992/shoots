"""The Judge's rules: does a shot meet an experiment's criteria? Pure.

Hard evidence first (decision 4). Each EXIF bound resolves to True, False or
None, where None means the tag was missing and nothing can be said. A single
False fails the shot whatever the model saw. The vision half is the
Analyst's confidence for the technique; it counts at or above a threshold.

    criteria met = no False in exif checks
             and every required technique seen at >= threshold
             and (some exif check is True, or there were no checkable bounds)

The last clause stops a photo with stripped EXIF from passing an experiment whose
whole point is a camera setting: if the experiment has bounds and none of them
could be checked, vision alone is not enough.
"""

from app.domain.entities import Analysis, Criteria, Exif, ExifRule, Experiment, Shot
from app.domain.experiment_criteria import VISUAL_GOALS

Check = bool | None


def check_exif(rule: ExifRule, exif: Exif) -> dict[str, Check]:
    """One entry per bound the rule sets; None when the tag is absent."""
    out: dict[str, Check] = {}
    t, f, iso = exif.exposure_time_s, exif.f_number, exif.iso
    focal = exif.focal_length_35mm or exif.focal_length_mm

    if rule.shutter_min_s is not None:
        out["shutter_min_s"] = None if t is None else t >= rule.shutter_min_s
    if rule.shutter_max_s is not None:
        out["shutter_max_s"] = None if t is None else t <= rule.shutter_max_s
    if rule.aperture_max is not None:
        out["aperture_max"] = None if f is None else f <= rule.aperture_max
    if rule.aperture_min is not None:
        out["aperture_min"] = None if f is None else f >= rule.aperture_min
    if rule.iso_min is not None:
        out["iso_min"] = None if iso is None else iso >= rule.iso_min
    if rule.iso_max is not None:
        out["iso_max"] = None if iso is None else iso <= rule.iso_max
    if rule.focal_min_mm is not None:
        out["focal_min_mm"] = None if focal is None else focal >= rule.focal_min_mm
    if rule.focal_max_mm is not None:
        out["focal_max_mm"] = None if focal is None else focal <= rule.focal_max_mm
    if rule.flash is not None:
        out["flash"] = None if exif.flash_fired is None else exif.flash_fired == rule.flash
    return out


def check_vision(required: list[str], analysis: Analysis | None) -> dict[str, float]:
    """Confidence per required technique; 0.0 when the Analyst did not tag it."""
    seen = {t.technique_id: t.confidence for t in analysis.techniques} if analysis else {}
    return {tid: seen.get(tid, 0.0) for tid in required}


def passes(
    exif_checks: dict[str, Check], vision_checks: dict[str, float], threshold: float
) -> bool:
    if any(v is False for v in exif_checks.values()):
        return False
    if any(conf < threshold for conf in vision_checks.values()):
        return False
    # Every declared bound must be known. Unknown is an abstention, not False.
    return all(v is True for v in exif_checks.values())


def abstention_reason(
    criteria: Criteria,
    exif_checks: dict[str, Check],
    vision_checks: dict[str, float],
    analysis: Analysis | None,
    threshold: float,
) -> str:
    """Why the Criteria cannot honestly be settled, or an empty string."""
    if any(value is False for value in exif_checks.values()):
        return ""  # hard evidence has already settled the result
    unknown = [name for name, value in exif_checks.items() if value is None]
    if unknown:
        return f"missing EXIF for {', '.join(unknown)}"
    visual_unsettled = [
        technique_id
        for technique_id in criteria.vision
        if vision_checks.get(technique_id, 0.0) < threshold
    ]
    if visual_unsettled and (analysis is None or analysis.abstained):
        return analysis.abstained if analysis and analysis.abstained else "no visual reading"
    if any(technique_id in VISUAL_GOALS for technique_id in visual_unsettled):
        return "Not enough visual Evidence to settle the declared focus relationship."
    return ""


def evaluate(
    criteria: Criteria, exif: Exif, analysis: Analysis | None, threshold: float
) -> tuple[bool, dict[str, Check], dict[str, float]]:
    exif_checks = check_exif(criteria.exif, exif)
    vision_checks = check_vision(criteria.vision, analysis)
    return passes(exif_checks, vision_checks, threshold), exif_checks, vision_checks


def is_submission(shot: Shot, experiment: Experiment) -> bool:
    """Only an explicit association makes a Shot an Experiment submission."""
    return bool(shot.experiment_id) and shot.experiment_id == experiment.id


def describe_checks(
    exif_checks: dict[str, Check], vision_checks: dict[str, float], threshold: float
) -> list[str]:
    """Plain lines for feedback fallback and the activity feed."""
    lines = []
    for name, result in exif_checks.items():
        state = "ok" if result else ("not met" if result is False else "could not check (no EXIF)")
        lines.append(f"{name.replace('_', ' ')}: {state}")
    for tid, conf in vision_checks.items():
        state = "seen" if conf >= threshold else "not seen"
        lines.append(f"{tid.replace('_', ' ')}: {state} ({conf:.0%})")
    return lines
