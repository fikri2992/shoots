"""What is wrong with a frame, decided by arithmetic. Pure.

The taxonomy names what a frame *has*. A teacher also names what it *does
wrong*, and names it precisely enough to act on: "1/25 s at 85 mm is under your
handheld limit, so that softness is shake" teaches something; "technical: 6"
does not. The rubric asks whether anything pulls against the frame and had no
vocabulary for the answer. This is that vocabulary.

Nothing here is asserted by a model. Every fault is computed from numbers the
pipeline already holds — the EXIF the camera wrote, the subject point and the
horizon row the Composer measured, the cells it named — so each one carries the
figure that produced it and a photographer can check the claim by looking. A
fault the arithmetic cannot settle is not raised at all: silence beats a guess
that the frame disproves.

Each fault is also excused by intent. A two-second exposure is not camera shake
when the frame is a light trail, and a subject filling the frame is not a
missing centre of interest when the technique *is* filling the frame. The
technique the panel agreed on is what tells them apart, which is why detection
runs after the vote and not before it.
"""

from app.domain import exposure
from app.domain import tone as tone_rules
from app.domain.entities import Exif, Fault, Tone
from app.domain.grid import Grid

CAMERA_SHAKE = "camera_shake"
OFF_GUIDE_SUBJECT = "off_guide_subject"
SPLIT_HORIZON = "split_horizon"
NO_CENTRE_OF_INTEREST = "no_centre_of_interest"
BLOWN_HIGHLIGHTS = "blown_highlights"
COLOUR_CAST = "colour_cast"

#: Every fault, with the short name a chip shows. The list is closed, like the
#: technique catalogue: a fault that is not here cannot be reported.
FAULTS: dict[str, str] = {
    CAMERA_SHAKE: "Camera shake",
    OFF_GUIDE_SUBJECT: "Subject off every line",
    SPLIT_HORIZON: "Horizon splits the frame",
    NO_CENTRE_OF_INTEREST: "No single centre of interest",
    BLOWN_HIGHLIGHTS: "Highlights blown to white",
    COLOUR_CAST: "Uncorrected colour cast",
}

#: Techniques whose whole point is a shutter below the handheld limit. On these
#: the blur is the photograph, so shake is never reported.
DELIBERATE_BLUR: frozenset[str] = frozenset(
    {"long_exposure", "light_trails", "panning", "icm", "zoom_burst", "astro", "light_painting"}
)
#: ... and the technique that says the camera was not in the photographer's hands.
BRACED: frozenset[str] = frozenset({"static_tripod"})

#: Techniques whose subject is meant to fill the frame.
WIDE_SUBJECT_OK: frozenset[str] = frozenset(
    {"fill_the_frame", "patterns", "break_the_pattern", "macro", "bokeh_balls"}
)

#: Techniques that put white in the frame on purpose. High key is mostly paper
#: white by definition, backlight and rim light burn the source out to keep the
#: edge, and a light trail or a painted light *is* the clipped part.
BRIGHT_ON_PURPOSE: frozenset[str] = frozenset(
    {"high_key", "backlight", "rim_light", "light_trails", "light_painting", "silhouette"}
)

#: Techniques that make the frame warm or cool on purpose, so its temperature
#: is the photograph and not an uncorrected white balance. Monochrome excuses
#: both directions: a frame with no colour cannot have the wrong colour.
WARM_ON_PURPOSE: frozenset[str] = frozenset(
    {"golden_hour", "warm_cool", "light_painting", "fill_flash", "monochrome", "low_key"}
)
COOL_ON_PURPOSE: frozenset[str] = frozenset(
    {"blue_hour", "warm_cool", "monochrome", "high_key", "astro"}
)

#: Share of the frame at pure white before the highlights are a fault rather
#: than a specular glint. Across the 19-frame corpus the median is 0.4% and the
#: 90th percentile 1.1%; at 2.0% this accuses the one frame that earns it.
BLOWN_SHARE = 2.0
#: How far from daylight a frame has to sit before its temperature is a cast.
#: The corpus runs 4322 K to 8639 K around a median of 5594 K, so these edges
#: leave the ordinary warm interior alone and accuse only the far ends.
#: Replayed over those 19 frames this reports nothing, which is the right
#: answer: the single frame past the cool edge sits at 8639 K and the panel
#: called it ``warm_cool``, so the excuse takes it. A fault that fires on a
#: corpus this small would be a fault with its edge in the wrong place.
WARM_CAST_K = 4000
COOL_CAST_K = 7500

#: The placement lines a photographer aims at, as fractions of the frame. Phi is
#: 1 : 0.618 : 1; the thirds are 1 : 1 : 1; the centre is the third choice a
#: composition can deliberately make. A subject near none of them was placed by
#: accident, and that is the only claim this fault makes.
PLACEMENT_LINES: tuple[tuple[float, str], ...] = (
    (1 / 3, "a third"),
    (2 / 3, "a third"),
    (0.382, "a phi line"),
    (0.618, "a phi line"),
    (0.5, "the centre"),
)

#: How near a line still counts as on it, in frame widths. Set to half the
#: widest gap between two adjacent lines (0.382 to 0.500), so the fault fires
#: only when the subject is nearer the empty middle of a gap than either side
#: of it. This is deliberately not the tolerance ``guides.refine`` works to:
#: choosing between two grids 0.049 apart needs a fine measure, while accusing
#: a photographer of placing nothing needs a coarse one. Replayed against 12
#: real frames, 0.024 accused 8 of them; this accuses the 1 that earns it.
ON_LINE_TOLERANCE = 0.06
#: Above this share of the grid, named cells describe a region and not a subject.
SUBJECT_SHARE = 1 / 3


def nearest_line(position: float) -> tuple[float, str, float]:
    """The placement line this position is closest to, and how far off it is."""
    at, label = min(PLACEMENT_LINES, key=lambda line: abs(line[0] - position))
    return at, label, abs(at - position)


def _shake(exif: Exif, seen: set[str]) -> Fault | None:
    derived = exposure.derive(exif)
    if derived.handheld_ok is not False or not exif.exposure_time_s:
        return None
    if seen & DELIBERATE_BLUR or seen & BRACED:
        return None
    focal = exif.focal_length_35mm or exif.focal_length_mm
    limit = exposure.shutter_text(derived.handheld_limit_s or 0.0)
    return Fault(
        fault_id=CAMERA_SHAKE,
        what="Any softness here is camera shake, not missed focus.",
        why=f"{exposure.shutter_text(exif.exposure_time_s)} at {focal:g} mm, "
        f"under the handheld limit of {limit}",
    )


def _off_guide(subject_x: float | None, subject_y: float | None) -> Fault | None:
    axes = [("across", subject_x), ("down", subject_y)]
    off = [
        (axis, value, nearest_line(value))
        for axis, value in axes
        if value is not None and nearest_line(value)[2] > ON_LINE_TOLERANCE
    ]
    if not off:
        return None
    axis, value, (at, label, distance) = max(off, key=lambda entry: entry[2][2])
    return Fault(
        fault_id=OFF_GUIDE_SUBJECT,
        what="The subject sits on no line the eye expects, so the frame reads unplaced.",
        why=f"{value:.2f} {axis}; the nearest line is {label} at {at:.2f}, "
        f"{distance:.2f} of the frame away",
    )


def _split_horizon(horizon_row: int | None, grid: Grid) -> Fault | None:
    """The horizon halves the frame when the middle falls inside its row."""
    if horizon_row is None or not (1 <= horizon_row <= grid.rows):
        return None
    top, bottom = (horizon_row - 1) / grid.rows, horizon_row / grid.rows
    if not top <= 0.5 <= bottom:
        return None
    return Fault(
        fault_id=SPLIT_HORIZON,
        what="The horizon cuts the frame into two equal halves, so neither one leads.",
        why=f"row {horizon_row} of {grid.rows} spans {top:.2f} to {bottom:.2f} "
        f"and the middle is 0.50",
    )


def _no_centre(subject_cells: list[str], grid: Grid, seen: set[str]) -> Fault | None:
    if not subject_cells or seen & WIDE_SUBJECT_OK:
        return None
    share = len(subject_cells) / grid.cell_count
    if share <= SUBJECT_SHARE:
        return None
    return Fault(
        fault_id=NO_CENTRE_OF_INTEREST,
        what="Nothing in the frame is clearly the subject; the eye has nowhere to land.",
        why=f"{len(subject_cells)} of {grid.cell_count} cells were named as subject, "
        f"{share:.0%} of the frame",
        cells=list(subject_cells),
    )


def _blown(tone: Tone, seen: set[str]) -> Fault | None:
    """Highlights past recovery. Measured off the pixels, so it holds on a
    phone export that threw its EXIF away."""
    if tone.clipped_high < BLOWN_SHARE or seen & BRIGHT_ON_PURPOSE:
        return None
    return Fault(
        fault_id=BLOWN_HIGHLIGHTS,
        what="The brightest areas are pure white with nothing in them; that detail "
        "cannot be brought back.",
        why=f"{tone.clipped_high:.1f}% of the frame is above 250 of 255, "
        f"against {BLOWN_SHARE:.0f}% where a highlight stops being a glint",
    )


def _cast(tone: Tone, seen: set[str]) -> Fault | None:
    """A white balance nobody asked for. The camera cannot tell us: every file
    in the corpus reports auto, so the temperature is measured off the frame
    and only the far ends of the scale are called."""
    if tone.cct_k is None:
        return None
    warm = tone.cct_k <= WARM_CAST_K
    cool = tone.cct_k >= COOL_CAST_K
    if warm and not seen & WARM_ON_PURPOSE:
        which, edge = "orange", WARM_CAST_K
    elif cool and not seen & COOL_ON_PURPOSE:
        which, edge = "blue", COOL_CAST_K
    else:
        return None
    return Fault(
        fault_id=COLOUR_CAST,
        what=f"The whole frame is pulled {which}; whites are not white, and no technique "
        "here makes that the point.",
        why=f"{tone.cct_k} K measured against {tone_rules.DAYLIGHT_K} K daylight, "
        f"past the {edge} K edge",
    )


def detect(
    exif: Exif,
    grid: Grid,
    technique_ids: list[str],
    subject_cells: list[str],
    subject_x: float | None = None,
    subject_y: float | None = None,
    horizon_row: int | None = None,
    tone: Tone | None = None,
) -> list[Fault]:
    """Every fault the numbers support, in the order a photographer would fix
    them: what cannot be recovered at all first, then the exposure — a shaken
    frame cannot be composed out of — then the framing."""
    seen = set(technique_ids)
    measured = tone if tone is not None else Tone()
    found = [
        _blown(measured, seen),
        _shake(exif, seen),
        _cast(measured, seen),
        _no_centre(subject_cells, grid, seen),
        _split_horizon(horizon_row, grid),
        _off_guide(subject_x, subject_y),
    ]
    return [fault for fault in found if fault is not None]
