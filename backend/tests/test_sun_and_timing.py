"""Solar times against published almanac values, and the delivery rule."""

from datetime import UTC, date, datetime, timedelta

from app.domain import timing
from app.domain.sun import sun_times

LONDON = (51.5074, -0.1278)
BANDUNG = (-6.9147, 107.6098)


def minutes_off(a: datetime, b: datetime) -> float:
    return abs((a - b).total_seconds()) / 60


def test_london_midsummer():
    # timeanddate: 2026-06-21 London sunrise 04:43 BST, sunset 21:21 BST.
    sun = sun_times(date(2026, 6, 21), *LONDON)
    assert minutes_off(sun.sunrise, datetime(2026, 6, 21, 3, 43, tzinfo=UTC)) < 4
    assert minutes_off(sun.sunset, datetime(2026, 6, 21, 20, 21, tzinfo=UTC)) < 4
    assert sun.dusk > sun.sunset > sun.sunrise > sun.dawn
    assert not sun.polar


def test_bandung_august():
    # Near the equator: about twelve hours of daylight, sunset ~17:50 WIB (10:50 UTC).
    sun = sun_times(date(2026, 8, 23), *BANDUNG)
    assert minutes_off(sun.sunset, datetime(2026, 8, 23, 10, 50, tzinfo=UTC)) < 8
    daylight = (sun.sunset - sun.sunrise).total_seconds() / 3600
    assert 11.5 < daylight < 12.5


def test_polar_day_is_flagged_not_crashed():
    assert sun_times(date(2026, 6, 21), 78.2, 15.6).polar


def test_golden_quest_lands_before_sunset():
    now = datetime(2026, 8, 23, 3, 0, tzinfo=UTC)  # 10:00 WIB
    t = timing.deliver_at(timing.GOLDEN, now, *BANDUNG)
    sun = sun_times(date(2026, 8, 23), *BANDUNG)
    assert t.anchor == "sunset"
    assert minutes_off(t.at, sun.sunset - timedelta(minutes=50)) < 1
    assert "sunset" in t.reason


def test_inside_the_window_means_now():
    sun = sun_times(date(2026, 8, 23), *BANDUNG)
    now = sun.sunset - timedelta(minutes=20)
    t = timing.deliver_at(timing.GOLDEN, now, *BANDUNG)
    assert t.at == now and t.reason.startswith("Now")


def test_after_sunset_rolls_to_the_next_window():
    sun = sun_times(date(2026, 8, 23), *BANDUNG)
    now = sun.sunset + timedelta(hours=2)
    t = timing.deliver_at(timing.GOLDEN, now, *BANDUNG)
    assert t.at > now
    assert t.anchor == "sunrise"  # the morning window comes first


def test_night_and_day_and_any():
    now = datetime(2026, 8, 23, 3, 0, tzinfo=UTC)
    night = timing.deliver_at(timing.NIGHT, now, *BANDUNG)
    assert night.anchor == "dusk" and night.at > now
    day = timing.deliver_at(timing.DAY, now, *BANDUNG)
    assert day.at == now and day.reason.startswith("Now")
    assert timing.deliver_at(timing.ANY, now, *BANDUNG).at == now
    assert timing.deliver_at(timing.GOLDEN, now, None, None).at == now
