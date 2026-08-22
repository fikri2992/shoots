"""Exposure arithmetic: what the camera settings imply, computed, not guessed.

The Technician lens and the Judge's feedback get these lines as facts, so
"1/40 s at 23 mm is inside the handheld limit" is arithmetic, not an
impression. Every formula is textbook:

* EV at ISO 100: ``log2(N² / t) - log2(ISO / 100)``; sunny-16 is EV 15.
* Handheld limit: ``1 / (2 × focal length)`` in 35 mm terms (the reciprocal
  rule with a stop of margin for high-resolution sensors).
* Star-trail ceiling: the 500 rule, ``500 / focal length``.
* Freezing motion: 1/500 s for people in motion, 1/1000 s for sport.

Sources are listed in docs/technique-evidence.md.
"""

import math
from dataclasses import dataclass

from app.domain.entities import Exif

SUNNY16_EV = 15.0
FREEZE_PEOPLE_S = 1 / 500
FREEZE_SPORT_S = 1 / 1000

#: Rough scene brightness by EV100, from the standard exposure-value table.
LIGHT_BANDS: tuple[tuple[float, str], ...] = (
    (15, "full sun"),
    (13, "hazy sun or bright overcast"),
    (11, "open shade or heavy overcast"),
    (9, "golden hour or a bright interior"),
    (7, "deep shade, dusk or an ordinary interior"),
    (4, "dim interior, blue hour or a lit street at night"),
    (-10, "near darkness"),
)


@dataclass(frozen=True)
class Derived:
    ev100: float | None
    light: str
    stops_from_sunny16: float | None
    handheld_limit_s: float | None
    handheld_ok: bool | None
    rule_500_s: float | None
    freezes_people: bool | None
    freezes_sport: bool | None


def ev100(shutter_s: float | None, f_number: float | None, iso: int | None) -> float | None:
    if not shutter_s or not f_number or not iso or shutter_s <= 0 or f_number <= 0 or iso <= 0:
        return None
    return math.log2(f_number**2 / shutter_s) - math.log2(iso / 100)


def light_band(ev: float) -> str:
    for floor, label in LIGHT_BANDS:
        if ev >= floor:
            return label
    return LIGHT_BANDS[-1][1]


def handheld_limit_s(focal_35mm: float | None) -> float | None:
    return 1 / (2 * focal_35mm) if focal_35mm and focal_35mm > 0 else None


def rule_500_s(focal_35mm: float | None) -> float | None:
    return 500 / focal_35mm if focal_35mm and focal_35mm > 0 else None


def derive(exif: Exif) -> Derived:
    focal = exif.focal_length_35mm or None
    ev = ev100(exif.exposure_time_s, exif.f_number, exif.iso)
    limit = handheld_limit_s(focal)
    shutter = exif.exposure_time_s
    return Derived(
        ev100=ev,
        light=light_band(ev) if ev is not None else "",
        stops_from_sunny16=(ev - SUNNY16_EV) if ev is not None else None,
        handheld_limit_s=limit,
        handheld_ok=(shutter <= limit) if (shutter and limit) else None,
        rule_500_s=rule_500_s(focal),
        freezes_people=(shutter <= FREEZE_PEOPLE_S) if shutter else None,
        freezes_sport=(shutter <= FREEZE_SPORT_S) if shutter else None,
    )


def shutter_text(seconds: float) -> str:
    return f"{seconds:g} s" if seconds >= 1 else f"1/{round(1 / seconds)} s"


def describe(exif: Exif) -> list[str]:
    """Plain lines for prompts. Empty when there is nothing to compute."""
    d = derive(exif)
    lines: list[str] = []
    if d.ev100 is not None:
        stops = d.stops_from_sunny16 or 0.0
        where = (
            f"{abs(stops):.1f} stops {'below' if stops < 0 else 'above'} sunny-16"
            if abs(stops) >= 0.5
            else "at sunny-16"
        )
        lines.append(f"EV {d.ev100:.1f} at ISO 100: {d.light} ({where})")
    if d.handheld_limit_s is not None and exif.exposure_time_s:
        state = "inside" if d.handheld_ok else "slower than"
        lines.append(
            f"handheld limit {shutter_text(d.handheld_limit_s)} for "
            f"{exif.focal_length_35mm} mm; {shutter_text(exif.exposure_time_s)} is {state} it"
            + ("" if d.handheld_ok else " (camera shake likely unless braced)")
        )
    if exif.exposure_time_s:
        if d.freezes_sport:
            lines.append("fast enough to freeze sport (1/1000 s or faster)")
        elif d.freezes_people:
            lines.append("fast enough to freeze people in motion, not sport")
        else:
            lines.append(
                f"slower than 1/500 s: moving subjects blur at {shutter_text(exif.exposure_time_s)}"
            )
    if d.rule_500_s is not None:
        lines.append(f"star-trail ceiling (500 rule) {d.rule_500_s:.0f} s at this focal length")
    return lines
