"""Findings are arithmetic, so every test here pins a number, not a mood."""

import pytest

from app.domain import findings
from app.domain.entities import Exif, Tone
from app.domain.grid import Grid

GRID = Grid(cols=7, rows=9, width=700, height=900)


def exif(shutter: float, focal: int = 85) -> Exif:
    return Exif(exposure_time_s=shutter, f_number=2.8, iso=400, focal_length_35mm=focal)


def ids(found: list) -> set[str]:
    return {finding.finding_id for finding in found}


def detect(**kwargs) -> list:
    base = dict(exif=Exif(), grid=GRID, technique_ids=[], subject_cells=[])
    return findings.detect(**{**base, **kwargs})


# --- camera shake ---------------------------------------------------------


def test_shake_is_named_when_the_shutter_is_under_the_handheld_limit():
    # The limit is 1/(2 x 85) = 1/170 s; 1/25 s is well under it.
    (finding,) = detect(exif=exif(1 / 25))
    assert finding.finding_id == findings.CAMERA_SHAKE
    assert "1/25 s at 85 mm" in finding.why and "1/170 s" in finding.why
    assert "risk of camera shake" in finding.what


def test_a_shutter_inside_the_limit_is_not_a_fault():
    assert detect(exif=exif(1 / 250)) == []


@pytest.mark.parametrize("technique", sorted(findings.DELIBERATE_BLUR))
def test_a_slow_shutter_the_technique_asked_for_is_not_shake(technique):
    assert detect(exif=exif(2.0), technique_ids=[technique]) == []


def test_a_tripod_excuses_the_slow_shutter_too():
    assert detect(exif=exif(2.0), technique_ids=["static_tripod"]) == []


def test_no_exif_means_no_claim():
    assert detect(exif=Exif()) == []


# --- subject placement ----------------------------------------------------


@pytest.mark.parametrize("position", [1 / 3, 2 / 3, 0.382, 0.618, 0.5])
def test_a_subject_on_any_line_is_not_a_fault(position):
    assert detect(subject_x=position, subject_y=position) == []


def test_distance_from_a_guide_is_neutral_evidence_not_a_finding():
    at, label, distance = findings.nearest_line(0.86)
    assert label == "a third" and at == pytest.approx(2 / 3)
    assert distance == pytest.approx(0.86 - 2 / 3)
    assert detect(subject_x=0.5, subject_y=0.86) == []


@pytest.mark.parametrize("position", [0.41, 0.44, 0.45, 0.55, 0.58, 0.71])
def test_a_subject_a_little_off_a_line_is_not_accused(position):
    """Replayed against 12 real frames, a 0.024 tolerance accused 8 of them.
    A finding that fires on two thirds of all frames teaches nobody anything and
    costs the trust that every other finding depends on."""
    assert detect(subject_x=position, subject_y=0.5) == []


def test_the_tolerance_is_half_the_widest_gap_between_lines():
    """So the finding means "nearer the empty middle of a gap than either line",
    which is a claim a photographer can check, and not a matter of taste."""
    lines = sorted(at for at, _ in findings.PLACEMENT_LINES)
    widest = max(b - a for a, b in zip(lines, lines[1:], strict=False))
    assert pytest.approx(widest / 2, abs=0.002) == findings.ON_LINE_TOLERANCE


# --- horizon --------------------------------------------------------------


def test_a_horizon_in_the_middle_is_neutral_evidence_not_a_finding():
    assert detect(horizon_row=5) == []


@pytest.mark.parametrize("row", [1, 3, 4, 6, 7, 9])
def test_a_horizon_off_the_middle_is_left_alone(row):
    assert detect(horizon_row=row) == []


def test_a_horizon_row_outside_the_grid_says_nothing():
    assert detect(horizon_row=99) == [] and detect(horizon_row=None) == []


def test_an_even_grid_splits_on_either_row_touching_the_middle():
    even = Grid(cols=8, rows=8, width=800, height=800)
    assert findings.detect(Exif(), even, [], [], horizon_row=4) == []
    assert findings.detect(Exif(), even, [], [], horizon_row=5) == []
    assert findings.detect(Exif(), even, [], [], horizon_row=3) == []


# --- centre of interest ---------------------------------------------------


def test_subject_area_share_does_not_claim_there_is_no_centre():
    cells = GRID.all_refs()[:25]  # 25 of 63
    assert detect(subject_cells=cells, subject_x=0.5, subject_y=0.5) == []


def test_a_third_of_the_grid_exactly_is_still_a_subject():
    assert detect(subject_cells=GRID.all_refs()[:21], subject_x=0.5, subject_y=0.5) == []


@pytest.mark.parametrize("technique", sorted(findings.WIDE_SUBJECT_OK))
def test_a_technique_that_fills_the_frame_excuses_its_own_subject(technique):
    found = detect(
        subject_cells=GRID.all_refs()[:40], technique_ids=[technique], subject_x=0.5, subject_y=0.5
    )
    assert found == []


# --- the whole set --------------------------------------------------------


def test_findings_come_back_in_the_order_a_photographer_would_fix_them():
    found = detect(
        exif=exif(1 / 25),
        subject_cells=GRID.all_refs()[:30],
        subject_x=0.86,
        subject_y=0.86,
        horizon_row=5,
    )
    assert [f.finding_id for f in found] == [findings.CAMERA_SHAKE]


# --- blown highlights -----------------------------------------------------


def test_highlights_past_recovery_are_named_with_the_share():
    (finding,) = detect(tone=Tone(cct_k=5500, clipped_high=8.3))
    assert finding.finding_id == findings.BLOWN_HIGHLIGHTS
    assert "8.3%" in finding.why and "250 of 255" in finding.why


def test_a_specular_glint_is_not_a_blown_frame():
    assert detect(tone=Tone(cct_k=5500, clipped_high=0.9)) == []


@pytest.mark.parametrize("technique", sorted(findings.BRIGHT_ON_PURPOSE))
def test_white_that_is_the_point_is_not_a_fault(technique: str):
    assert detect(tone=Tone(cct_k=5500, clipped_high=40.0), technique_ids=[technique]) == []


# --- colour cast ----------------------------------------------------------


def test_a_blue_frame_with_nothing_to_explain_it_is_a_cast():
    (finding,) = detect(tone=Tone(cct_k=8639))
    assert finding.finding_id == findings.COLOUR_CAST
    assert "8639 K" in finding.why and "5500 K" in finding.why
    assert "blue" in finding.what


def test_a_warm_frame_with_nothing_to_explain_it_is_a_cast():
    (finding,) = detect(tone=Tone(cct_k=3200))
    assert finding.finding_id == findings.COLOUR_CAST
    assert "orange" in finding.what


def test_daylight_is_not_a_cast():
    assert detect(tone=Tone(cct_k=5594)) == []
    assert detect(tone=Tone(cct_k=4322)) == []
    assert detect(tone=Tone(cct_k=7000)) == []


@pytest.mark.parametrize("technique", sorted(findings.COOL_ON_PURPOSE))
def test_a_cool_frame_the_panel_explains_is_not_a_cast(technique: str):
    assert detect(tone=Tone(cct_k=8639), technique_ids=[technique]) == []


@pytest.mark.parametrize("technique", sorted(findings.WARM_ON_PURPOSE))
def test_a_warm_frame_the_panel_explains_is_not_a_cast(technique: str):
    assert detect(tone=Tone(cct_k=3200), technique_ids=[technique]) == []


def test_an_unmeasured_frame_is_never_accused_of_colour():
    """No tone at all must read as silence, not as a neutral default."""
    assert detect() == []
    assert detect(tone=Tone()) == []


def test_a_clean_frame_has_nothing_said_about_it():
    assert detect(exif=exif(1 / 250), subject_cells=["D3"], subject_x=1 / 3, subject_y=2 / 3) == []


def test_guide_choice_stays_finer_than_fault_tolerance():
    """The two measures answer different questions and must not be merged: the
    guide picks between grids 0.049 apart, the finding asks whether the subject
    was placed at all."""
    from app.domain import guides

    assert guides.refine("thirds", 0.38, 0.5) == guides.PHI
    assert detect(subject_x=0.38, subject_y=0.5) == []


def test_every_fault_carries_a_number_and_a_catalogue_name():
    found = detect(
        exif=exif(1 / 25),
        subject_cells=GRID.all_refs()[:30],
        subject_x=0.86,
        subject_y=0.86,
        horizon_row=5,
        tone=Tone(cct_k=8639, clipped_high=8.3),
    )
    assert len(found) == len(findings.ACTIVE_FINDINGS)
    for finding in found:
        assert finding.finding_id in findings.ACTIVE_FINDINGS
        assert findings.ACTIVE_FINDINGS[finding.finding_id] and finding.what.endswith(".")
        assert any(character.isdigit() for character in finding.why), finding.finding_id
