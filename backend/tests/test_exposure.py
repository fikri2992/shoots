from app.domain import exposure
from app.domain.entities import Exif


def test_sunny_sixteen_is_ev_fifteen():
    assert abs(exposure.ev100(1 / 125, 16, 100) - 15.0) < 0.2
    # same light, ISO 400 at f/16 needs 1/500
    assert abs(exposure.ev100(1 / 500, 16, 400) - 15.0) < 0.2
    assert exposure.ev100(None, 2.8, 100) is None


def test_handheld_and_freeze_and_500_rule():
    d = exposure.derive(Exif(exposure_time_s=1 / 40, f_number=1.7, iso=320, focal_length_35mm=23))
    assert abs(d.handheld_limit_s - 1 / 46) < 1e-6
    assert d.handheld_ok is False  # 1/40 s is a touch slower than the 1/46 s limit
    assert d.freezes_people is False
    assert abs(d.rule_500_s - 21.7) < 0.1
    assert 5 < d.ev100 < 5.5 and d.light == "dim interior, blue hour or a lit street at night"
    slow = exposure.derive(Exif(exposure_time_s=1 / 10, focal_length_35mm=50))
    assert slow.handheld_ok is False and slow.ev100 is None


def test_describe_lines_are_plain_and_numeric():
    lines = exposure.describe(
        Exif(exposure_time_s=1 / 2000, f_number=5.6, iso=200, focal_length_35mm=200)
    )
    assert any("freeze sport" in line for line in lines)
    assert any("handheld limit 1/400 s" in line for line in lines)
    assert any(line.startswith("EV ") for line in lines)
    assert exposure.describe(Exif()) == []
