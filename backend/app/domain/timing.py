"""When a quest should land on the phone.

A technique has a light window (``taxonomy.LIGHT``); the user's last known
location comes from the EXIF of their own frames. From those two facts the
Scout decides *when* to deliver, not just what: a golden-hour quest arrives
fifty minutes before sunset where you last shot, a night quest after dusk.
Nothing here needs a timezone: instants are UTC, the phone shows local time.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.sun import SunTimes, sun_times

#: The light windows a technique can ask for.
GOLDEN = "golden"
BLUE = "blue"
NIGHT = "night"
DAY = "day"
ANY = "any"

#: If the window opens within this, send now rather than make the phone wait.
SOON = timedelta(minutes=5)


@dataclass(frozen=True)
class Timing:
    at: datetime
    light: str
    reason: str
    anchor: str = ""  # sunrise | sunset | dusk — what the time is relative to
    anchor_at: datetime | None = None


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime
    reason: str
    anchor: str
    anchor_at: datetime


def windows(light: str, sun: SunTimes, next_sun: SunTimes) -> list[Window]:
    """The windows for one light kind on one day, in order."""
    m = timedelta(minutes=1)
    if light == GOLDEN:
        return [
            Window(
                sun.sunrise - 10 * m,
                sun.sunrise + 45 * m,
                "Morning golden hour starts at sunrise where you last shot.",
                "sunrise",
                sun.sunrise,
            ),
            Window(
                sun.sunset - 50 * m,
                sun.sunset + 10 * m,
                "Golden hour: fifty minutes before sunset where you last shot.",
                "sunset",
                sun.sunset,
            ),
        ]
    if light == BLUE:
        return [
            Window(
                sun.dawn - 5 * m,
                sun.sunrise - 10 * m,
                "Blue hour before sunrise where you last shot.",
                "sunrise",
                sun.sunrise,
            ),
            Window(
                sun.sunset + 10 * m,
                sun.dusk + 15 * m,
                "Blue hour: the twenty minutes after sunset where you last shot.",
                "sunset",
                sun.sunset,
            ),
        ]
    if light == NIGHT:
        return [
            Window(
                sun.dusk + 45 * m,
                next_sun.dawn - 60 * m,
                "Full dark: an hour after dusk where you last shot.",
                "dusk",
                sun.dusk,
            )
        ]
    if light == DAY:
        return [
            Window(
                sun.sunrise + 150 * m,
                sun.sunset - 120 * m,
                "High sun: hard light and short shadows.",
                "sunrise",
                sun.sunrise,
            )
        ]
    return []


def deliver_at(
    light: str, now: datetime, latitude: float | None, longitude: float | None
) -> Timing:
    """The instant to deliver, and why, for a technique's light window."""
    if light == ANY or light not in {GOLDEN, BLUE, NIGHT, DAY}:
        return Timing(now, ANY, "Any light works for this one.")
    if latitude is None or longitude is None:
        return Timing(
            now, light, "No location in your recent frames yet, so this one comes right away."
        )

    day = now.date() - timedelta(days=1)
    candidates: list[Window] = []
    for offset in range(4):
        d = day + timedelta(days=offset)
        sun = sun_times(d, latitude, longitude)
        next_sun = sun_times(d + timedelta(days=1), latitude, longitude)
        candidates.extend(windows(light, sun, next_sun))
    candidates.sort(key=lambda w: w.start)

    for window in candidates:
        if window.start <= now <= window.end:
            return Timing(now, light, "Now: " + window.reason, window.anchor, window.anchor_at)
        if window.start > now:
            at = now if window.start - now <= SOON else window.start
            return Timing(at, light, window.reason, window.anchor, window.anchor_at)
    return Timing(now, light, "Could not find the light window; sent now.")
