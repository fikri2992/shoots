"""Sunrise, sunset and dusk for a place and a date. NOAA's solar equations,
accurate to a couple of minutes, which is all a "go out before sunset"
decision needs. Pure; no tz database: everything is UTC and the phone
formats it.
"""

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

#: Zenith angles: the sun's upper limb on the horizon, and civil twilight.
SUNRISE_ZENITH = 90.833
CIVIL_ZENITH = 96.0


@dataclass(frozen=True)
class SunTimes:
    sunrise: datetime
    sunset: datetime
    dawn: datetime  # civil: enough light to see by
    dusk: datetime  # civil: the sky goes deep blue after this
    polar: bool = False  # no rise/set on this day; the times are nominal


def sun_times(day: date, latitude: float, longitude: float) -> SunTimes:
    """UTC instants for ``day`` (the UTC date) at the given place."""
    n = day.timetuple().tm_yday
    gamma = 2 * math.pi / 365 * (n - 1 + 0.5)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    midnight = datetime(day.year, day.month, day.day, tzinfo=UTC)

    def hour_angle(zenith: float) -> float | None:
        lat = math.radians(latitude)
        value = math.cos(math.radians(zenith)) / (math.cos(lat) * math.cos(decl)) - math.tan(
            lat
        ) * math.tan(decl)
        if value < -1 or value > 1:
            return None
        return math.degrees(math.acos(value))

    def at(minutes: float) -> datetime:
        return midnight + timedelta(minutes=minutes)

    ha = hour_angle(SUNRISE_ZENITH)
    ha_civil = hour_angle(CIVIL_ZENITH)
    polar = ha is None
    if ha is None:
        # Midnight sun or polar night: pretend a 12-hour day around solar noon.
        ha = 90.0
    if ha_civil is None:
        ha_civil = ha + 6.0
    noon = 720 - 4 * longitude - eqtime
    return SunTimes(
        sunrise=at(noon - 4 * ha),
        sunset=at(noon + 4 * ha),
        dawn=at(noon - 4 * ha_civil),
        dusk=at(noon + 4 * ha_civil),
        polar=polar,
    )
