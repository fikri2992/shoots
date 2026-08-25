"""Frame → ``entities.Tone``. Colour and tone measured off the pixels.

The camera will not tell us. Every file in the corpus carries
``WhiteBalance: 0`` (auto) and ``LightSource: 255`` (other), so EXIF records
that the camera chose and never what it chose. A claim about colour that
rests on a lens's adjective is not evidence; the same claim with 8639 K
beside it is.

Measured on a thumbnail, deliberately. Colour temperature, saturation and
tonal range are properties of the whole frame, and a 256 px long edge holds
them to well within the precision anyone can act on while keeping the pass
cheap enough to run on every ingest.

Formulae:

* sRGB → linear → CIE XYZ with the sRGB D65 matrix, then chromaticity
  ``x, y``; CCT by McCamy's cubic, which is within a few kelvin of the exact
  Planckian locus over the range daylight photography lives in.
* Luminance is Rec. 601 ``0.299R + 0.587G + 0.114B``, matching what the eye
  weights and what every histogram in a camera shows.
* Hue families are the twelve 30° sectors of the HSV wheel, counted only over
  pixels saturated enough to have a hue at all.
"""

import math

import numpy as np
from PIL import Image

from app.domain.entities import Tone

#: Long edge the measurement runs at.
SAMPLE_EDGE = 256

#: Below this saturation a pixel is a grey with a rounding error, not a colour,
#: and counting its hue would make every frame look analogous.
HUE_FLOOR = 0.15

#: What counts as a white-balance reference: a pixel neutral enough to carry
#: the light's colour rather than an object's, bright enough to carry any at
#: all, and short of clipping, where the channels are pinned and the hue is a
#: fiction. Black is not a neutral reference — it is the absence of one.
NEUTRAL_MAX_SATURATION = 0.25
REFERENCE_MIN_LUMA = 60
REFERENCE_MAX_LUMA = 250

#: How much of the frame has to be a usable reference before a colour
#: temperature is worth reporting.
#:
#: This is the guard Duv alone does not give. Saturated orange sits *near* the
#: Planckian locus — which is why tungsten light is orange — so a low-key
#: portrait against a burnt-orange backdrop passes the Duv test and then reports
#: 1637 K, candlelight, about a frame that was nothing of the kind. Its mean is
#: the subject's colour, because there is no white anywhere in it to balance
#: against. Neutral share alone does not catch it either: that frame reads 48%
#: "neutral" because it is largely black, and black carries no colour at all.
#:
#: Measured over the corpus, the frames that produced a nonsense temperature
#: hold 0.0-2.9% lit neutral and every frame whose reading looks right holds
#: 9.3% or more. At 5% the four frames with no reference lose their temperature
#: and every other frame keeps one.
MIN_REFERENCE_SHARE = 0.05
#: Saturation a colour has to reach to be an accent rather than the palette.
ACCENT_SATURATION = 0.55
#: Where the scale runs out and detail with it, on 0-255.
CLIP_HIGH = 250
CLIP_LOW = 5

#: The twelve hue sectors, by the name a photographer would use, starting at 0°.
HUE_NAMES: tuple[str, ...] = (
    "red",
    "orange",
    "amber",
    "yellow",
    "lime",
    "green",
    "teal",
    "cyan",
    "azure",
    "blue",
    "violet",
    "magenta",
)
#: Hue sectors that read warm and cool. The remainder (lime, teal, violet,
#: magenta) sit on the boundary and are counted as neither, so ``warm_share``
#: and ``cool_share`` do not sum to one and are not meant to.
WARM_HUES = frozenset({"red", "orange", "amber", "yellow"})
COOL_HUES = frozenset({"cyan", "azure", "blue", "green"})


def _linear(channel: np.ndarray) -> np.ndarray:
    """sRGB transfer curve, inverted. Averaging gamma-encoded values would
    weight the shadows wrongly and pull every measured temperature warm."""
    c = channel / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


#: Ohno's polynomial for the Planckian locus in the CIE 1960 UCS plane, used to
#: get Duv — how far off the locus a chromaticity sits.
_DUV_K = (
    -0.471106,
    1.925865,
    -2.4243787,
    1.5317403,
    -0.5179722,
    0.0893944,
    -0.00616793,
)

#: How far off the Planckian locus a frame may sit and still have a colour
#: temperature worth reporting. Correlated colour temperature is only defined
#: near the locus: a frame of pure red is not 2655 K light, it is a red object,
#: and reporting the number would have the cast fault accusing a vivid sunset of
#: an uncorrected tungsten white balance.
#:
#: Measured over the 19-frame corpus, real photographs span -0.0416 to +0.0167
#: — a whole frame averages toward neutral however vivid its subject is — while
#: a flat saturated primary sits at 0.11. At 0.05 every real frame keeps its
#: temperature and the chromaticities where the number would be fiction lose it.
MAX_DUV = 0.05


def duv(cx: float, cy: float) -> float:
    """Signed distance from the Planckian locus in CIE 1960 UCS (Ohno 2011).
    Positive is above the locus (greener), negative below (more magenta)."""
    denominator = -2 * cx + 12 * cy + 3
    if denominator == 0:
        return float("inf")
    u, v = 4 * cx / denominator, 6 * cy / denominator
    length = math.hypot(u - 0.292, v - 0.24)
    if length == 0:
        return 0.0
    angle = math.acos(max(-1.0, min(1.0, (u - 0.292) / length)))
    locus = sum(k * angle**i for i, k in enumerate(_DUV_K))
    return length - locus


def chromaticity(mean_rgb: tuple[float, float, float]) -> tuple[float, float] | None:
    """CIE 1931 x, y of a mean sRGB triple."""
    r, g, b = (float(_linear(np.array([c], dtype=np.float64))[0]) for c in mean_rgb)
    x = 0.4124 * r + 0.3576 * g + 0.1805 * b
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = 0.0193 * r + 0.1192 * g + 0.9505 * b
    total = x + y + z
    return (x / total, y / total) if total > 0 else None


def cct_kelvin(mean_rgb: tuple[float, float, float]) -> int | None:
    """Correlated colour temperature of a mean sRGB triple, by McCamy.

    None when the chromaticity is too far off the Planckian locus for a
    temperature to mean anything, which is the honest answer for a frame whose
    average colour is an object rather than a light.
    """
    point = chromaticity(mean_rgb)
    if point is None:
        return None
    cx, cy = point
    if abs(duv(cx, cy)) > MAX_DUV:
        return None
    # McCamy's epicentre. A frame sitting exactly on it has no defined slope.
    if abs(cy - 0.1858) < 1e-6:
        return None
    n = (cx - 0.3320) / (0.1858 - cy)
    kelvin = 449 * n**3 + 3525 * n**2 + 6823.3 * n + 5520.33
    # Outside this the cubic is extrapolating past anything it was fitted on,
    # and a number no one can act on is worse than no number.
    if not 1000 <= kelvin <= 40000:
        return None
    return int(round(kelvin))


def measure(image: Image.Image) -> Tone:
    """Everything ``domain/tone.py`` needs, in one pass over a thumbnail."""
    sample = image.convert("RGB")
    sample.thumbnail((SAMPLE_EDGE, SAMPLE_EDGE), Image.LANCZOS)
    rgb = np.asarray(sample, dtype=np.float32)
    if rgb.size == 0:
        return Tone()

    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    p5, p95 = (float(v) for v in np.percentile(luma, (5, 95)))

    hsv = np.asarray(sample.convert("HSV"), dtype=np.float32) / 255.0
    hue, sat = hsv[..., 0], hsv[..., 1]

    # White balance is estimated off what the light fell on, not off the frame's
    # average: the average of a frame with no white in it is the subject.
    reference = (
        (sat < NEUTRAL_MAX_SATURATION) & (luma > REFERENCE_MIN_LUMA) & (luma < REFERENCE_MAX_LUMA)
    )
    kelvin = None
    if float(np.mean(reference)) >= MIN_REFERENCE_SHARE:
        kelvin = cct_kelvin(
            (float(r[reference].mean()), float(g[reference].mean()), float(b[reference].mean()))
        )

    coloured = sat >= HUE_FLOOR
    hues: list[str] = []
    opposition: int | None = None
    if coloured.any():
        sectors = np.floor(hue[coloured] * 12).astype(int) % 12
        counts = np.bincount(sectors, minlength=12)
        ranked = [int(i) for i in np.argsort(counts)[::-1] if counts[i]]
        hues = [HUE_NAMES[i] for i in ranked[:3]]
        if len(ranked) >= 2:
            gap = abs(ranked[0] - ranked[1]) * 30
            opposition = int(min(gap, 360 - gap))

    warm = _share(hue, sat, WARM_HUES)
    cool = _share(hue, sat, COOL_HUES)

    return Tone(
        cct_k=kelvin,
        cast=round(float(r.mean() - b.mean()), 1),
        saturation=round(float(sat.mean()) * 100, 1),
        saturation_p95=round(float(np.percentile(sat, 95)) * 100, 1),
        accent_share=round(float(np.mean(sat >= ACCENT_SATURATION)) * 100, 1),
        warm_share=round(warm * 100, 1),
        cool_share=round(cool * 100, 1),
        luma_mean=round(float(luma.mean()), 1),
        luma_p5=round(p5, 1),
        luma_p95=round(p95, 1),
        clipped_high=round(float(np.mean(luma > CLIP_HIGH)) * 100, 2),
        clipped_low=round(float(np.mean(luma < CLIP_LOW)) * 100, 2),
        hues=hues,
        hue_opposition=opposition,
    )


def _share(hue: np.ndarray, sat: np.ndarray, names: frozenset[str]) -> float:
    """Share of the whole frame whose hue falls in ``names`` and is saturated
    enough to count. Of the frame, not of the coloured pixels: a frame that is
    90% grey with a warm corner is not a warm frame."""
    sectors = np.floor(hue * 12).astype(int) % 12
    wanted = np.zeros(12, dtype=bool)
    for index, name in enumerate(HUE_NAMES):
        wanted[index] = name in names
    return float(np.mean(wanted[sectors] & (sat >= HUE_FLOOR)))
