"""Declared goals and equipment context, separate from recognition heuristics."""

import re

from app.domain.entities import CameraCapabilities, Criteria, ExifRule
from app.domain.taxonomy import Technique

VISUAL_GOALS = {
    "deep_dof": "Nearby and distant detail are both visibly sharp.",
    "shallow_dof": "The subject is sharp against a visibly out-of-focus background.",
    "bokeh_balls": "Out-of-focus point lights appear as soft discs behind the subject.",
}


def for_technique(technique: Technique, text: list[str]) -> Criteria:
    """Do not confuse a common camera recipe with a necessary visible outcome."""
    if technique.id in VISUAL_GOALS:
        return Criteria(vision=[technique.id], text=[VISUAL_GOALS[technique.id]])
    return Criteria(
        exif=ExifRule(**technique.exif),
        vision=[technique.id],
        text=[line.strip() for line in text if line.strip()][:4],
    )


def equipment_context(reports: list[CameraCapabilities]) -> str:
    lines = [
        "Device-reported Camera Capabilities. This is not proof of the Camera used "
        "for this Shot or the next one. EXIF reports one exposure, not available controls. "
        "Unreported controls remain unknown. Never assume aperture priority or manual "
        "aperture control. Do not merge lenses into one adjustable aperture."
    ]
    if not reports:
        lines.append("No Camera Capabilities reported.")
    for report in reports:
        lines.append(f"Device: {report.manufacturer} {report.model}")
        if not report.cameras:
            lines.append("Camera aperture capabilities unknown.")
        for camera in report.cameras:
            values = camera.apertures
            if not values:
                detail = "aperture capability unknown"
            elif len(values) == 1:
                detail = f"fixed f/{values[0]:g}; no aperture choice exposed"
            else:
                detail = "exposes apertures " + ", ".join(f"f/{v:g}" for v in values)
            lines.append(f"Camera {camera.camera_id}, {camera.facing}: {detail}.")
    return "\n".join(lines)


def validate_visual_advice(technique_id: str, text: str) -> None:
    """Fail closed when generated visual-goal advice reintroduces an aperture recipe."""
    if technique_id not in VISUAL_GOALS:
        return
    if re.search(
        r"\bf\s*[/\-]?\s*\d|\bf[ -]?stop\b|\baperture[ -]priority\b|"
        r"\b(?:stop(?:ping)?\s+down|(?:open|close|narrow|widen|set|adjust|change)\w*"
        r"\s+(?:\w+\s+){0,3}aperture)\b",
        text,
        re.IGNORECASE,
    ):
        raise ValueError("Visual-goal advice prescribed an aperture control; draft not used")
