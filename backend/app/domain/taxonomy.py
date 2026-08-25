"""The technique catalogue: the finite vocabulary the whole product speaks.

Every agent refers to techniques by ``id``. The Analyst may only tag ids from
this list; the Scout may only issue experiments for ids from this list; the skill
graph has exactly one node per id. Open-ended "discover a technique" is not a
thing here, on purpose: a finite taxonomy is what makes the graph legible and
the Judge checkable.

Each technique carries two kinds of evidence:

* ``exif``  — hard, machine-checkable bounds on camera settings. The Judge
  applies these first and they are never a matter of opinion.
* ``cue``   — what the Analyst is told to look for in the frame. Soft evidence
  with a confidence, counted only above ``settings.judge_min_confidence``.

``requires`` lists prerequisites. The Scout issues an experiment only when every
prerequisite is at least *attempted*, so experiments climb rather than jump.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class Family(StrEnum):
    COMPOSITION = "composition"
    LIGHT = "light"
    EXPOSURE = "exposure"
    LENS = "lens"
    COLOR = "color"
    VIDEO = "video"


#: Allowed keys of an exif rule; mirrors ``entities.ExifRule`` exactly.
EXIF_RULE_KEYS = frozenset(
    {
        "shutter_max_s",
        "shutter_min_s",
        "aperture_max",
        "aperture_min",
        "iso_min",
        "iso_max",
        "focal_min_mm",
        "focal_max_mm",
        "flash",
    }
)


@dataclass(frozen=True)
class Technique:
    id: str
    name: str
    family: Family
    #: 1 = first week with a camera, 3 = deliberate practice.
    level: int
    #: What the Analyst looks for. Written for the model, in the second person.
    cue: str
    #: Hard bounds the Judge checks when EXIF is present.
    exif: dict[str, float | int | bool] = field(default_factory=dict)
    requires: tuple[str, ...] = ()

    @property
    def light(self) -> str:
        """When the light is right for it (domain/timing.py). Default: any time."""
        return LIGHT.get(self.id, "any")

    @property
    def needs(self) -> tuple[str, ...]:
        """Gear it cannot be done without; the Scout respects the user's constraints."""
        return NEEDS.get(self.id, ())

    @property
    def video_only(self) -> bool:
        return self.family is Family.VIDEO


def _t(
    id: str,
    name: str,
    family: Family,
    level: int,
    cue: str,
    exif: dict | None = None,
    requires: tuple[str, ...] = (),
) -> Technique:
    return Technique(id, name, family, level, cue, exif or {}, requires)


TECHNIQUES: tuple[Technique, ...] = (
    # --- composition ------------------------------------------------------
    _t(
        "rule_of_thirds",
        "Rule of thirds",
        Family.COMPOSITION,
        1,
        "The main subject sits on a thirds line or intersection, not dead centre.",
    ),
    _t(
        "centre_composition",
        "Deliberate centre",
        Family.COMPOSITION,
        1,
        "The subject is centred on purpose, with symmetry or emptiness around it making the "
        "choice read as intentional.",
    ),
    _t(
        "horizon_placement",
        "Horizon placement",
        Family.COMPOSITION,
        1,
        "A level horizon placed on the upper or lower third, never cutting the frame in half.",
    ),
    _t(
        "leading_lines",
        "Leading lines",
        Family.COMPOSITION,
        1,
        "Roads, rails, edges or shadows that pull the eye from the frame edge to the subject.",
    ),
    _t(
        "fill_the_frame",
        "Fill the frame",
        Family.COMPOSITION,
        1,
        "The subject occupies most of the frame; background is minimal or absent.",
    ),
    _t(
        "negative_space",
        "Negative space",
        Family.COMPOSITION,
        2,
        "A small subject against a large, quiet area that gives it room and scale.",
        requires=("fill_the_frame",),
    ),
    _t(
        "frame_within_frame",
        "Frame within a frame",
        Family.COMPOSITION,
        2,
        "Doorways, windows, arches or foliage enclosing the subject inside the photo's frame.",
    ),
    _t(
        "symmetry",
        "Symmetry",
        Family.COMPOSITION,
        2,
        "A mirrored composition, left-right or top-bottom, with the axis near the frame centre.",
        requires=("centre_composition",),
    ),
    _t(
        "reflections",
        "Reflections",
        Family.COMPOSITION,
        2,
        "Water, glass or wet ground doubling the subject; the reflection is part of the design.",
        requires=("symmetry",),
    ),
    _t(
        "layering",
        "Foreground, midground, background",
        Family.COMPOSITION,
        2,
        "Three distinct depth planes, each with something in it, giving the image depth.",
        requires=("leading_lines",),
    ),
    _t(
        "patterns",
        "Patterns and repetition",
        Family.COMPOSITION,
        2,
        "A repeating element fills the frame: windows, tiles, people, trees.",
    ),
    _t(
        "break_the_pattern",
        "Break the pattern",
        Family.COMPOSITION,
        3,
        "A repeating pattern with exactly one element that breaks it, and that element is the "
        "subject.",
        requires=("patterns",),
    ),
    _t(
        "diagonals",
        "Diagonals",
        Family.COMPOSITION,
        2,
        "Strong diagonal lines or a tilted arrangement that creates tension and movement.",
    ),
    _t(
        "low_angle",
        "Low angle",
        Family.COMPOSITION,
        1,
        "Camera well below eye level, looking up; subjects gain height and drama.",
    ),
    _t(
        "high_angle",
        "High angle / top-down",
        Family.COMPOSITION,
        1,
        "Camera above the subject looking down, flattening the scene into shapes.",
    ),
    _t(
        "silhouette",
        "Silhouette",
        Family.COMPOSITION,
        2,
        "The subject is a clean black shape against a much brighter background.",
        requires=("backlight",),
    ),
    _t(
        "minimalism",
        "Minimalism",
        Family.COMPOSITION,
        3,
        "Very few elements, large plain areas, one clear subject. Nothing you could remove.",
        requires=("negative_space",),
    ),
    _t(
        "juxtaposition",
        "Juxtaposition",
        Family.COMPOSITION,
        3,
        "Two contrasting subjects placed together so the contrast is the point: old/new, "
        "big/small.",
        requires=("layering",),
    ),
    _t(
        "rule_of_odds",
        "Rule of odds",
        Family.COMPOSITION,
        2,
        "An odd number of subjects, usually three, arranged so one is the anchor.",
    ),
    _t(
        "eye_contact_portrait",
        "Eye-level portrait",
        Family.COMPOSITION,
        1,
        "A person at eye level, eyes sharp and on or near the upper third.",
    ),
    # --- light ------------------------------------------------------------
    _t(
        "golden_hour",
        "Golden hour",
        Family.LIGHT,
        1,
        "Warm, low, directional sunlight with long soft shadows; skin and surfaces glow orange.",
    ),
    _t(
        "blue_hour",
        "Blue hour",
        Family.LIGHT,
        2,
        "Deep blue ambient sky after sunset or before sunrise, often with artificial lights on.",
        requires=("golden_hour",),
    ),
    _t(
        "backlight",
        "Backlight",
        Family.LIGHT,
        1,
        "The main light is behind the subject; edges glow, the front is shadowed or the scene "
        "is hazy.",
    ),
    _t(
        "rim_light",
        "Rim light",
        Family.LIGHT,
        2,
        "A bright outline along the subject's edge separating it from a dark background.",
        requires=("backlight",),
    ),
    _t(
        "window_light",
        "Window light",
        Family.LIGHT,
        1,
        "Soft directional light from one side, from a window, with a gentle falloff across "
        "the subject.",
    ),
    _t(
        "rembrandt",
        "Rembrandt lighting",
        Family.LIGHT,
        3,
        "A portrait with a small triangle of light on the shadow-side cheek under the eye.",
        requires=("window_light",),
    ),
    _t(
        "split_light",
        "Split lighting",
        Family.LIGHT,
        2,
        "Half the face lit, half in shadow, split along the nose.",
        requires=("window_light",),
    ),
    _t(
        "hard_light",
        "Hard light and shadow",
        Family.LIGHT,
        2,
        "Crisp, hard-edged shadows from a small or direct light source; the shadow is a subject.",
    ),
    _t(
        "soft_light",
        "Soft overcast light",
        Family.LIGHT,
        1,
        "Shadowless or nearly shadowless light from an overcast sky or large diffuser.",
    ),
    _t(
        "high_key",
        "High key",
        Family.LIGHT,
        2,
        "Mostly bright tones, minimal shadow, white or near-white background.",
        requires=("soft_light",),
    ),
    _t(
        "low_key",
        "Low key",
        Family.LIGHT,
        2,
        "Mostly dark tones; a single light picks out the subject and everything else falls "
        "to black.",
        requires=("hard_light",),
    ),
    _t(
        "chiaroscuro",
        "Chiaroscuro",
        Family.LIGHT,
        3,
        "Extreme light-dark contrast used to model a three-dimensional subject, painterly.",
        requires=("low_key", "rembrandt"),
    ),
    _t(
        "dappled_light",
        "Dappled light",
        Family.LIGHT,
        2,
        "Patches of sunlight through leaves or a screen falling on the subject.",
    ),
    _t(
        "fill_flash",
        "Fill flash",
        Family.LIGHT,
        2,
        "Daylight scene where flash lifted the shadows on a backlit subject; catchlights in eyes.",
        exif={"flash": True},
        requires=("backlight",),
    ),
    _t(
        "light_painting",
        "Light painting",
        Family.LIGHT,
        3,
        "Long exposure in the dark with a moved light drawing streaks or shapes.",
        exif={"shutter_min_s": 2.0},
        requires=("long_exposure",),
    ),
    # --- exposure ---------------------------------------------------------
    _t(
        "shallow_dof",
        "Shallow depth of field",
        Family.EXPOSURE,
        1,
        "Subject sharp, background strongly blurred; a clear plane of focus.",
        exif={"aperture_max": 2.8},
    ),
    _t(
        "deep_dof",
        "Deep depth of field",
        Family.EXPOSURE,
        1,
        "Front to back sharpness, typical of landscapes.",
        exif={"aperture_min": 8.0},
    ),
    _t(
        "freeze_action",
        "Freeze action",
        Family.EXPOSURE,
        1,
        "Fast movement stopped dead: droplets, wings, a jump, no motion blur.",
        exif={"shutter_max_s": 1 / 500},
    ),
    _t(
        "panning",
        "Panning",
        Family.EXPOSURE,
        2,
        "Moving subject sharp, background streaked horizontally from following it.",
        exif={"shutter_min_s": 1 / 125, "shutter_max_s": 1 / 8},
        requires=("freeze_action",),
    ),
    _t(
        "long_exposure",
        "Long exposure",
        Family.EXPOSURE,
        2,
        "Water turned to mist, clouds streaked, moving people ghosted; static parts sharp.",
        exif={"shutter_min_s": 0.5},
        requires=("deep_dof",),
    ),
    _t(
        "light_trails",
        "Light trails",
        Family.EXPOSURE,
        2,
        "Vehicle lights drawn as continuous lines through a night scene.",
        exif={"shutter_min_s": 2.0},
        requires=("long_exposure",),
    ),
    _t(
        "high_iso_night",
        "Handheld night",
        Family.EXPOSURE,
        2,
        "A dark scene shot handheld, grain accepted, highlights held.",
        exif={"iso_min": 3200},
    ),
    _t(
        "astro",
        "Night sky",
        Family.EXPOSURE,
        3,
        "Stars or the Milky Way visible as points, foreground as a silhouette or lit.",
        exif={"shutter_min_s": 8.0, "iso_min": 1600},
        requires=("long_exposure", "high_iso_night"),
    ),
    _t(
        "icm",
        "Intentional camera movement",
        Family.EXPOSURE,
        3,
        "The whole frame is painterly blur from moving the camera during a slow exposure.",
        exif={"shutter_min_s": 1 / 8},
        requires=("panning",),
    ),
    _t(
        "zoom_burst",
        "Zoom burst",
        Family.EXPOSURE,
        3,
        "Radial streaks toward the centre from zooming during the exposure.",
        exif={"shutter_min_s": 1 / 8},
        requires=("icm",),
    ),
    # --- lens -------------------------------------------------------------
    _t(
        "wide_angle",
        "Wide-angle drama",
        Family.LENS,
        1,
        "Exaggerated perspective, near things huge, converging lines.",
        exif={"focal_max_mm": 24},
    ),
    _t(
        "telephoto_compression",
        "Telephoto compression",
        Family.LENS,
        2,
        "Distant layers stacked flat and large: a moon behind a building, mountains behind a town.",
        exif={"focal_min_mm": 135},
    ),
    _t(
        "normal_portrait",
        "Portrait focal length",
        Family.LENS,
        1,
        "A face at a flattering 50-85mm equivalent, no wide-angle distortion.",
        exif={"focal_min_mm": 45, "focal_max_mm": 90},
    ),
    _t(
        "macro",
        "Macro detail",
        Family.LENS,
        2,
        "A small subject filling the frame with detail invisible to the eye: texture, insects, "
        "water.",
    ),
    _t(
        "bokeh_balls",
        "Bokeh highlights",
        Family.LENS,
        2,
        "Out-of-focus point lights rendered as soft discs behind the subject.",
        exif={"aperture_max": 2.8},
        requires=("shallow_dof",),
    ),
    # --- color ------------------------------------------------------------
    _t(
        "monochrome",
        "Black and white",
        Family.COLOR,
        1,
        "No colour; the image works on tone, shape and contrast alone.",
    ),
    _t(
        "complementary",
        "Complementary colours",
        Family.COLOR,
        2,
        "Two opposite hues dominate: orange/teal, red/green, yellow/purple.",
    ),
    _t(
        "single_accent",
        "Single accent colour",
        Family.COLOR,
        2,
        "A mostly neutral or muted frame with one small saturated colour that is the subject.",
        requires=("monochrome",),
    ),
    _t(
        "warm_cool",
        "Warm against cool",
        Family.COLOR,
        2,
        "Warm light or subject set against cool shadow or sky.",
        requires=("golden_hour",),
    ),
    _t(
        "muted_palette",
        "Muted palette",
        Family.COLOR,
        2,
        "Low saturation throughout, tones close together, a calm mood.",
    ),
    _t(
        "colour_blocking",
        "Colour blocking",
        Family.COLOR,
        3,
        "Large flat areas of bold colour meeting at clean edges.",
        requires=("complementary", "minimalism"),
    ),
    # --- video ------------------------------------------------------------
    _t(
        "static_tripod",
        "Locked-off shot",
        Family.VIDEO,
        1,
        "Across the frames the framing does not move at all; only the subject moves.",
    ),
    _t(
        "pan",
        "Pan",
        Family.VIDEO,
        1,
        "The camera rotates horizontally; background slides sideways across the frames at a "
        "steady rate.",
    ),
    _t(
        "tilt",
        "Tilt",
        Family.VIDEO,
        1,
        "The camera rotates vertically, revealing from bottom to top or the reverse.",
    ),
    _t(
        "push_in",
        "Push in / dolly",
        Family.VIDEO,
        2,
        "The camera physically moves toward the subject; parallax between foreground and "
        "background.",
        requires=("static_tripod",),
    ),
    _t(
        "tracking",
        "Tracking shot",
        Family.VIDEO,
        2,
        "The camera moves alongside a moving subject, keeping it in the same place in frame.",
        requires=("pan",),
    ),
    _t(
        "orbit",
        "Orbit",
        Family.VIDEO,
        3,
        "The camera circles the subject; the background rotates behind it.",
        requires=("tracking",),
    ),
    _t(
        "reveal",
        "Reveal",
        Family.VIDEO,
        2,
        "Something blocks the view at first and the camera move uncovers the subject.",
        requires=("pan", "tilt"),
    ),
    _t(
        "rack_focus",
        "Rack focus",
        Family.VIDEO,
        2,
        "Focus shifts from one plane to another within the shot; two subjects trade sharpness.",
        requires=("shallow_dof",),
    ),
    _t(
        "slow_motion",
        "Slow motion",
        Family.VIDEO,
        2,
        "High frame rate footage: motion is smooth and slowed, fine detail in movement.",
        requires=("freeze_action",),
    ),
    _t(
        "timelapse",
        "Timelapse",
        Family.VIDEO,
        2,
        "Long spans compressed: clouds race, shadows sweep, crowds blur.",
        requires=("static_tripod", "long_exposure"),
    ),
    _t(
        "whip_pan",
        "Whip pan",
        Family.VIDEO,
        3,
        "A pan so fast the frames smear, usually used to hide a cut.",
        requires=("pan",),
    ),
    _t(
        "match_cut",
        "Match cut",
        Family.VIDEO,
        3,
        "Two consecutive shots where shape or motion lines up across the cut.",
        requires=("reveal",),
    ),
)

BY_ID: dict[str, Technique] = {t.id: t for t in TECHNIQUES}


class TaxonomyError(ValueError):
    pass


def get(technique_id: str) -> Technique:
    try:
        return BY_ID[technique_id]
    except KeyError as exc:
        raise TaxonomyError(f"unknown technique: {technique_id!r}") from exc


def by_family(family: Family) -> list[Technique]:
    return [t for t in TECHNIQUES if t.family is family]


def unlocked(attempted: set[str]) -> list[Technique]:
    """Techniques whose prerequisites are all in ``attempted`` and which are not
    themselves attempted yet. This is the Scout's candidate list."""
    return [
        t
        for t in TECHNIQUES
        if t.id not in attempted and all(req in attempted for req in t.requires)
    ]


#: Light window per technique (domain/timing.py): golden | blue | night | day.
#: Not listed = any time. Kept here, not on the entries, so the whole timing
#: policy is one table.
LIGHT: dict[str, str] = {
    "golden_hour": "golden",
    "backlight": "golden",
    "rim_light": "golden",
    "silhouette": "golden",
    "warm_cool": "golden",
    "blue_hour": "blue",
    "long_exposure": "blue",
    "light_trails": "night",
    "high_iso_night": "night",
    "astro": "night",
    "light_painting": "night",
    "bokeh_balls": "night",
    "hard_light": "day",
    "dappled_light": "day",
}

#: Gear a technique cannot be done without. Matched against what the user
#: told the Coach they lack.
NEEDS: dict[str, tuple[str, ...]] = {
    "long_exposure": ("tripod",),
    "light_trails": ("tripod",),
    "astro": ("tripod",),
    "light_painting": ("tripod",),
    "static_tripod": ("tripod",),
    "timelapse": ("tripod",),
    "telephoto_compression": ("telephoto",),
    "macro": ("macro",),
    "fill_flash": ("flash",),
}


def validate() -> None:
    """Catalogue invariants. Run by the test suite and at import in dev."""
    ids = {t.id for t in TECHNIQUES}
    for table_name, table in (("LIGHT", LIGHT), ("NEEDS", NEEDS)):
        for tid in table:
            if tid not in ids:
                raise TaxonomyError(f"{table_name}: unknown technique {tid}")
    seen: set[str] = set()
    for t in TECHNIQUES:
        if t.id in seen:
            raise TaxonomyError(f"duplicate id {t.id}")
        seen.add(t.id)
        if t.level not in (1, 2, 3):
            raise TaxonomyError(f"{t.id}: level must be 1-3")
        if t.light not in {"golden", "blue", "night", "day", "any"}:
            raise TaxonomyError(f"{t.id}: unknown light window {t.light}")
        unknown = set(t.exif) - EXIF_RULE_KEYS
        if unknown:
            raise TaxonomyError(f"{t.id}: unknown exif keys {sorted(unknown)}")
        if (
            "shutter_min_s" in t.exif
            and "shutter_max_s" in t.exif
            and t.exif["shutter_min_s"] > t.exif["shutter_max_s"]
        ):
            raise TaxonomyError(f"{t.id}: shutter bounds inverted")
    for t in TECHNIQUES:
        for req in t.requires:
            if req not in seen:
                raise TaxonomyError(f"{t.id} requires unknown {req!r}")
            if BY_ID[req].level > t.level:
                raise TaxonomyError(
                    f"{t.id} (L{t.level}) requires harder {req} (L{BY_ID[req].level})"
                )
    # No cycles: every technique must be reachable from the empty set by repeated unlocking.
    attempted: set[str] = set()
    while True:
        step = unlocked(attempted)
        if not step:
            break
        attempted.update(t.id for t in step)
    if len(attempted) != len(TECHNIQUES):
        stuck = sorted(seen - attempted)
        raise TaxonomyError(f"unreachable techniques (cycle?): {stuck}")
