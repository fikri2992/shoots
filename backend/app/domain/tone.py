"""Colour and tone arithmetic: what the pixels imply, computed, not guessed. Pure.

``domain/exposure.py`` sits on ``Exif`` and turns camera settings into facts.
This sits on ``Tone`` and does the same for everything the camera did not
record. It exists because the colour and light families were the two halves of
the panel making claims with nothing behind them: measured over the corpus they
fire at 0.94 and 1.06 sightings a shot, comparable to exposure's 0.94, and
until now every one of them arrived as an adjective while a composition claim
arrived with a grid reference, a guide and a percentage.

The bands are photographic convention, not invention:

* Colour temperature against the daylight locus — tungsten near 3200 K, noon
  daylight 5500 K, overcast 6500 K, open shade 7500 K and up.
* Key from mean luminance, the axis high-key and low-key actually name.
* Tonal range as the spread between the 5th and 95th percentiles, which is what
  a histogram's usable width means and what chiaroscuro pushes to the limit.

Where a band edge is a judgement rather than a convention it was placed against
the 19-frame corpus and the count it accuses is written beside it.
"""

from dataclasses import dataclass
from datetime import UTC, timedelta

from app.domain import sun
from app.domain.entities import Exif, Tone

#: Reference points on the daylight locus, warmest first.
TEMPERATURE_BANDS: tuple[tuple[int, str], ...] = (
    (7500, "open shade or a heavy blue cast"),
    (6500, "overcast daylight"),
    (5800, "midday daylight"),
    (5000, "early or late daylight"),
    (4200, "a warm interior or late golden light"),
    (3200, "tungsten"),
    (0, "candle or sodium light"),
)
#: Noon daylight, the neutral everything else is described against.
DAYLIGHT_K = 5500

#: Mean luminance on 0-255. The corpus sits between 59 and 146, so these edges
#: describe frames rather than sort this corpus: nothing here is high key.
KEY_BANDS: tuple[tuple[float, str], ...] = (
    (170, "high key"),
    (85, "mid key"),
    (0, "low key"),
)

#: Spread between the 5th and 95th percentiles of luminance.
RANGE_BANDS: tuple[tuple[float, str], ...] = (
    (180, "the full range"),
    (120, "an ordinary range"),
    (0, "a flat, compressed range"),
)

#: Mean HSV saturation as a percentage. Corpus median is 24.9 and the two ends
#: are 9.2 and 55.1, so "restrained" is the ordinary frame and both edges name
#: something a photographer would have done on purpose.
PALETTE_BANDS: tuple[tuple[float, str], ...] = (
    (45, "vivid"),
    (30, "saturated"),
    (15, "restrained"),
    (0, "near-neutral"),
)

#: Degrees apart the two dominant hues have to be to read as opposed rather
#: than as neighbours. Complementary pairs sit at 180; the corpus splits cleanly
#: into a cluster at 30 (twelve frames, all analogous) and a tail at 120-180.
COMPLEMENTARY_MIN = 120
ANALOGOUS_MAX = 60

#: Within this of sunrise or sunset the light is what photographers call golden.
#: The usual figure is the hour either side.
GOLDEN_WINDOW = timedelta(hours=1)


@dataclass(frozen=True)
class Derived:
    temperature: str
    kelvin_from_daylight: int | None
    key: str
    tonal_range: float
    range_band: str
    palette: str
    harmony: str


def band(value: float, bands: tuple[tuple[float, str], ...]) -> str:
    for floor, label in bands:
        if value >= floor:
            return label
    return bands[-1][1]


def harmony_of(tone: Tone) -> str:
    """What the two dominant hues are doing to each other."""
    if tone.saturation < PALETTE_BANDS[-2][0]:
        return "near-neutral: too little colour for a hue relationship"
    if tone.hue_opposition is None:
        return ""
    if tone.hue_opposition >= COMPLEMENTARY_MIN:
        return "opposed, the complementary relationship"
    if tone.hue_opposition <= ANALOGOUS_MAX:
        return "neighbouring, an analogous palette"
    return "a split relationship, neither opposed nor neighbouring"


def derive(tone: Tone) -> Derived:
    return Derived(
        temperature=band(tone.cct_k, TEMPERATURE_BANDS) if tone.cct_k else "",
        kelvin_from_daylight=(tone.cct_k - DAYLIGHT_K) if tone.cct_k else None,
        key=band(tone.luma_mean, KEY_BANDS),
        tonal_range=round(tone.luma_p95 - tone.luma_p5, 1),
        range_band=band(tone.luma_p95 - tone.luma_p5, RANGE_BANDS),
        palette=band(tone.saturation, PALETTE_BANDS),
        harmony=harmony_of(tone),
    )


def solar_context(exif: Exif) -> str:
    """Where the sun was when the frame was taken, when the camera recorded
    enough to say. Golden hour and blue hour are claims about the sun's
    position, so they are the two light techniques that can be checked rather
    than believed — the same NOAA equations the Scout times experiments with."""
    if exif.captured_at is None or exif.latitude is None or exif.longitude is None:
        return ""
    when = exif.captured_at
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    times = sun.sun_times(when.date(), exif.latitude, exif.longitude)
    if times.polar:
        return "no sunrise or sunset at this latitude on this date"
    for label, at in (("sunrise", times.sunrise), ("sunset", times.sunset)):
        gap = when - at
        if abs(gap) <= GOLDEN_WINDOW:
            side = "after" if gap >= timedelta(0) else "before"
            return f"shot {abs(gap).seconds // 60} minutes {side} {label}: golden hour"
    if when < times.dawn or when > times.dusk:
        return "shot with the sun below civil twilight: night, not blue hour"
    if when < times.sunrise or when > times.sunset:
        return "shot between civil twilight and the horizon: blue hour"
    midday = times.sunrise + (times.sunset - times.sunrise) / 2
    hours = abs((when - midday).total_seconds()) / 3600
    return f"shot {hours:.1f} hours from solar noon, sun well up: not golden or blue hour"


def _measured(tone: Tone) -> bool:
    return tone.cct_k is not None or tone.luma_mean > 0


def technical(tone: Tone) -> list[str]:
    """For the Technician: where the frame ran out of scale. Exposure's half of
    tone, and the half a lens judging sharpness and noise should be holding."""
    if not _measured(tone):
        return []
    d = derive(tone)
    lines = [
        f"tonal range {d.tonal_range:.0f} of 255, p5 {tone.luma_p5:.0f} to "
        f"p95 {tone.luma_p95:.0f}: {d.range_band}"
    ]
    if tone.clipped_high or tone.clipped_low:
        lines.append(
            f"{tone.clipped_high:.2f}% of the frame is clipped to white and "
            f"{tone.clipped_low:.2f}% crushed to black — no detail recoverable either way"
        )
    else:
        lines.append("nothing is clipped to white or crushed to black")
    return lines


def light(tone: Tone, exif: Exif | None = None) -> list[str]:
    """For the Composer: the temperature and the key, which is what the light
    family is actually claiming about. Solar position where the camera wrote
    enough to place the sun, because golden hour and blue hour are the two
    light techniques that can be checked rather than believed."""
    if not _measured(tone):
        return []
    d = derive(tone)
    lines: list[str] = []
    if tone.cct_k:
        offset = d.kelvin_from_daylight or 0
        against = (
            f"{abs(offset)} K {'above' if offset > 0 else 'below'} daylight"
            if abs(offset) >= 300
            else "on daylight"
        )
        lines.append(f"colour temperature {tone.cct_k} K: {d.temperature} ({against})")
    lines.append(
        f"mean luminance {tone.luma_mean:.0f} of 255: {d.key}; "
        f"the spread p5 to p95 is {d.tonal_range:.0f}, {d.range_band}"
    )
    if exif is not None:
        solar = solar_context(exif)
        if solar:
            lines.append(solar)
    return lines


def palette(tone: Tone) -> list[str]:
    """For the Storyteller: how much colour there is and what it is doing.
    The colour family's evidence, which until now was an adjective."""
    if not _measured(tone):
        return []
    d = derive(tone)
    lines = [
        f"saturation {tone.saturation:.0f}% mean, {tone.saturation_p95:.0f}% at the 95th "
        f"percentile: a {d.palette} palette"
    ]
    if tone.hues:
        joined = " and ".join(tone.hues[:2])
        gap = f", {tone.hue_opposition}° apart on the wheel" if tone.hue_opposition else ""
        lines.append(f"dominant hues {joined}{gap}" + (f" — {d.harmony}" if d.harmony else ""))
    if abs(tone.cast) >= 5:
        which = "warm" if tone.cast > 0 else "cool"
        lines.append(
            f"{which} overall: mean red is {abs(tone.cast):.0f} points "
            f"{'above' if tone.cast > 0 else 'below'} mean blue on 0-255"
        )
    lines.append(
        f"{tone.warm_share:.0f}% of the frame reads warm by hue and {tone.cool_share:.0f}% cool; "
        f"{tone.accent_share:.0f}% is strongly saturated (a single accent is a small share "
        f"of an otherwise quiet frame)"
    )
    return lines


def describe(tone: Tone, exif: Exif | None = None) -> list[str]:
    """Every measured line, deduplicated. The feed, the Synthesizer and the
    Judge get the whole picture; a lens gets only its own half, so the panel
    keeps the independence that makes its vote worth taking."""
    lines: list[str] = []
    for group in (light(tone, exif), palette(tone), technical(tone)):
        for entry in group:
            if entry not in lines:
                lines.append(entry)
    return lines
