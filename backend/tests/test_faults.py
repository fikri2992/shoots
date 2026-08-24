"""Faults are arithmetic, so every test here pins a number, not a mood."""

import pytest

from app.domain import faults
from app.domain.entities import Exif
from app.domain.grid import Grid

GRID = Grid(cols=7, rows=9, width=700, height=900)


def exif(shutter: float, focal: int = 85) -> Exif:
    return Exif(exposure_time_s=shutter, f_number=2.8, iso=400, focal_length_35mm=focal)


def ids(found: list) -> set[str]:
    return {fault.fault_id for fault in found}


def detect(**kwargs) -> list:
    base = dict(exif=Exif(), grid=GRID, technique_ids=[], subject_cells=[])
    return faults.detect(**{**base, **kwargs})


# --- camera shake ---------------------------------------------------------


def test_shake_is_named_when_the_shutter_is_under_the_handheld_limit():
    # The limit is 1/(2 x 85) = 1/170 s; 1/25 s is well under it.
    (fault,) = detect(exif=exif(1 / 25))
    assert fault.fault_id == faults.CAMERA_SHAKE
    assert "1/25 s at 85 mm" in fault.why and "1/170 s" in fault.why
    assert "not missed focus" in fault.what


def test_a_shutter_inside_the_limit_is_not_a_fault():
    assert detect(exif=exif(1 / 250)) == []


@pytest.mark.parametrize("technique", sorted(faults.DELIBERATE_BLUR))
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


def test_a_subject_near_no_line_at_all_is_a_fault_with_its_distance():
    # 0.86 is 0.19 from the nearest line, a third at 0.667. Nothing put it there.
    (fault,) = detect(subject_x=0.5, subject_y=0.86)
    assert fault.fault_id == faults.OFF_GUIDE_SUBJECT
    assert "0.86 down" in fault.why and "a third at 0.67" in fault.why


def test_the_worse_axis_is_the_one_reported():
    (fault,) = detect(subject_x=0.44, subject_y=0.9)
    assert "0.90 down" in fault.why


@pytest.mark.parametrize("position", [0.41, 0.44, 0.45, 0.55, 0.58, 0.71])
def test_a_subject_a_little_off_a_line_is_not_accused(position):
    """Replayed against 12 real frames, a 0.024 tolerance accused 8 of them.
    A fault that fires on two thirds of all frames teaches nobody anything and
    costs the trust that every other fault depends on."""
    assert detect(subject_x=position, subject_y=0.5) == []


def test_the_tolerance_is_half_the_widest_gap_between_lines():
    """So the fault means "nearer the empty middle of a gap than either line",
    which is a claim a photographer can check, and not a matter of taste."""
    lines = sorted(at for at, _ in faults.PLACEMENT_LINES)
    widest = max(b - a for a, b in zip(lines, lines[1:], strict=False))
    assert pytest.approx(widest / 2, abs=0.002) == faults.ON_LINE_TOLERANCE


# --- horizon --------------------------------------------------------------


def test_a_horizon_on_the_middle_row_splits_the_frame():
    (fault,) = detect(horizon_row=5)  # rows 1-9; row 5 spans 0.44 to 0.56
    assert fault.fault_id == faults.SPLIT_HORIZON
    assert "row 5 of 9" in fault.why


@pytest.mark.parametrize("row", [1, 3, 4, 6, 7, 9])
def test_a_horizon_off_the_middle_is_left_alone(row):
    assert detect(horizon_row=row) == []


def test_a_horizon_row_outside_the_grid_says_nothing():
    assert detect(horizon_row=99) == [] and detect(horizon_row=None) == []


def test_an_even_grid_splits_on_either_row_touching_the_middle():
    even = Grid(cols=8, rows=8, width=800, height=800)
    assert ids(faults.detect(Exif(), even, [], [], horizon_row=4)) == {faults.SPLIT_HORIZON}
    assert ids(faults.detect(Exif(), even, [], [], horizon_row=5)) == {faults.SPLIT_HORIZON}
    assert faults.detect(Exif(), even, [], [], horizon_row=3) == []


# --- centre of interest ---------------------------------------------------


def test_a_subject_over_a_third_of_the_grid_is_not_a_subject():
    cells = GRID.all_refs()[:25]  # 25 of 63
    (fault,) = detect(subject_cells=cells, subject_x=0.5, subject_y=0.5)
    assert fault.fault_id == faults.NO_CENTRE_OF_INTEREST
    assert "25 of 63" in fault.why and "40%" in fault.why
    assert fault.cells == cells


def test_a_third_of_the_grid_exactly_is_still_a_subject():
    assert detect(subject_cells=GRID.all_refs()[:21], subject_x=0.5, subject_y=0.5) == []


@pytest.mark.parametrize("technique", sorted(faults.WIDE_SUBJECT_OK))
def test_a_technique_that_fills_the_frame_excuses_its_own_subject(technique):
    found = detect(
        subject_cells=GRID.all_refs()[:40], technique_ids=[technique], subject_x=0.5, subject_y=0.5
    )
    assert found == []


# --- the whole set --------------------------------------------------------


def test_faults_come_back_in_the_order_a_photographer_would_fix_them():
    found = detect(
        exif=exif(1 / 25),
        subject_cells=GRID.all_refs()[:30],
        subject_x=0.86,
        subject_y=0.86,
        horizon_row=5,
    )
    assert [f.fault_id for f in found] == [
        faults.CAMERA_SHAKE,
        faults.NO_CENTRE_OF_INTEREST,
        faults.SPLIT_HORIZON,
        faults.OFF_GUIDE_SUBJECT,
    ]


def test_a_clean_frame_has_nothing_said_about_it():
    assert detect(exif=exif(1 / 250), subject_cells=["D3"], subject_x=1 / 3, subject_y=2 / 3) == []


def test_guide_choice_stays_finer_than_fault_tolerance():
    """The two measures answer different questions and must not be merged: the
    guide picks between grids 0.049 apart, the fault asks whether the subject
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
    )
    assert len(found) == 4
    for fault in found:
        assert fault.fault_id in faults.FAULTS
        assert faults.FAULTS[fault.fault_id] and fault.what.endswith(".")
        assert any(character.isdigit() for character in fault.why), fault.fault_id
