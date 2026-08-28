"""Finite visual strategy routing for every still Technique.

The table chooses an explanation grammar. It does not claim that a detector
succeeded and it never promotes Technique Evidence. Imaging code may attempt
the listed strategies in order and must retain an explicit fallback.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.domain import taxonomy


class VisualStrategyKind(StrEnum):
    GUIDE = "guide"
    POINT = "point"
    REGION = "region"
    PATHS = "paths"
    ENCLOSURE = "enclosure"
    AXIS = "axis"
    PAIR = "pair"
    INSTANCES = "instances"
    PLANES = "planes"
    LUMINANCE = "luminance"
    HUE = "hue"
    SATURATION = "saturation"
    SHARPNESS = "sharpness"
    NOISE = "noise"
    EDGES = "edges"
    BOKEH = "bokeh"
    BLUR_DIRECTION = "blur_direction"
    RADIAL_BLUR = "radial_blur"
    FACE_LANDMARKS = "face_landmarks"
    DEPTH = "depth"
    EXIF = "exif"


@dataclass(frozen=True)
class TechniqueVisualPlan:
    primary: VisualStrategyKind
    supporting: tuple[VisualStrategyKind, ...] = ()
    fallback: VisualStrategyKind = VisualStrategyKind.REGION


def _p(
    primary: VisualStrategyKind,
    *supporting: VisualStrategyKind,
    fallback: VisualStrategyKind = VisualStrategyKind.REGION,
) -> TechniqueVisualPlan:
    return TechniqueVisualPlan(primary, supporting, fallback)


S = VisualStrategyKind

PLANS: dict[str, TechniqueVisualPlan] = {
    # Composition
    "rule_of_thirds": _p(S.GUIDE, S.POINT),
    "centre_composition": _p(S.AXIS, S.POINT),
    "horizon_placement": _p(S.AXIS, S.EDGES),
    "leading_lines": _p(S.PATHS, S.EDGES),
    "fill_the_frame": _p(S.REGION),
    "negative_space": _p(S.REGION, S.EDGES),
    "frame_within_frame": _p(S.ENCLOSURE, S.REGION),
    "symmetry": _p(S.AXIS, S.EDGES),
    "reflections": _p(S.PAIR, S.AXIS),
    "layering": _p(S.PLANES, S.DEPTH),
    "patterns": _p(S.INSTANCES, S.EDGES),
    "break_the_pattern": _p(S.INSTANCES, S.POINT),
    "diagonals": _p(S.PATHS, S.EDGES),
    "low_angle": _p(S.PATHS, S.DEPTH),
    "high_angle": _p(S.PLANES, S.DEPTH),
    "silhouette": _p(S.LUMINANCE, S.REGION),
    "minimalism": _p(S.REGION, S.EDGES),
    "juxtaposition": _p(S.PAIR, S.REGION),
    "rule_of_odds": _p(S.INSTANCES, S.POINT),
    "eye_contact_portrait": _p(S.FACE_LANDMARKS, S.SHARPNESS, S.GUIDE),
    # Light
    "golden_hour": _p(S.HUE, S.LUMINANCE, S.EXIF),
    "blue_hour": _p(S.HUE, S.LUMINANCE, S.EXIF),
    "backlight": _p(S.LUMINANCE, S.REGION),
    "rim_light": _p(S.LUMINANCE, S.EDGES),
    "window_light": _p(S.LUMINANCE, S.REGION),
    "rembrandt": _p(S.FACE_LANDMARKS, S.LUMINANCE),
    "split_light": _p(S.FACE_LANDMARKS, S.LUMINANCE, S.AXIS),
    "hard_light": _p(S.LUMINANCE, S.EDGES),
    "soft_light": _p(S.LUMINANCE, S.EDGES),
    "high_key": _p(S.LUMINANCE),
    "low_key": _p(S.LUMINANCE),
    "chiaroscuro": _p(S.LUMINANCE, S.REGION),
    "dappled_light": _p(S.LUMINANCE, S.INSTANCES),
    "fill_flash": _p(S.EXIF, S.FACE_LANDMARKS, S.LUMINANCE),
    "light_painting": _p(S.PATHS, S.LUMINANCE, S.EXIF),
    # Exposure
    "shallow_dof": _p(S.SHARPNESS, S.PAIR, S.EXIF),
    "deep_dof": _p(S.SHARPNESS, S.PLANES, S.EXIF),
    "freeze_action": _p(S.EXIF, S.SHARPNESS, S.REGION),
    "motion_blur": _p(S.BLUR_DIRECTION, S.PAIR),
    "panning": _p(S.BLUR_DIRECTION, S.SHARPNESS, S.EXIF),
    "long_exposure": _p(S.EXIF, S.BLUR_DIRECTION, S.PAIR),
    "light_trails": _p(S.PATHS, S.LUMINANCE, S.EXIF),
    "high_iso_night": _p(S.NOISE, S.EXIF, S.LUMINANCE),
    "astro": _p(S.INSTANCES, S.LUMINANCE, S.EXIF),
    "icm": _p(S.BLUR_DIRECTION, fallback=S.LUMINANCE),
    "zoom_burst": _p(S.RADIAL_BLUR, fallback=S.LUMINANCE),
    # Lens
    "wide_angle": _p(S.EXIF, S.PATHS, S.DEPTH),
    "telephoto_compression": _p(S.EXIF, S.PLANES, S.DEPTH),
    "normal_portrait": _p(S.EXIF, S.FACE_LANDMARKS),
    "macro": _p(S.SHARPNESS, S.REGION),
    "bokeh_balls": _p(S.BOKEH, S.SHARPNESS),
    # Colour
    "monochrome": _p(S.SATURATION),
    "complementary": _p(S.HUE, S.PAIR),
    "single_accent": _p(S.HUE, S.POINT),
    "warm_cool": _p(S.HUE, S.PAIR),
    "muted_palette": _p(S.SATURATION),
    "colour_blocking": _p(S.HUE, S.REGION),
}


def plan_for(technique_id: str) -> TechniqueVisualPlan:
    """Return the locked still-Technique plan or reject unsupported input."""
    technique = taxonomy.get(technique_id)
    if technique.video_only:
        raise ValueError(f"video Technique has no still visual plan: {technique_id}")
    try:
        return PLANS[technique_id]
    except KeyError as exc:  # startup validation should make this unreachable
        raise ValueError(f"still Technique has no visual plan: {technique_id}") from exc


def validate() -> None:
    still_ids = {item.id for item in taxonomy.TECHNIQUES if not item.video_only}
    missing = still_ids - PLANS.keys()
    extra = PLANS.keys() - still_ids
    if missing or extra:
        raise ValueError(f"visual plans mismatch: missing={sorted(missing)}, extra={sorted(extra)}")


validate()
