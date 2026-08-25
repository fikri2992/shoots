"""Camera movement, checked against clips whose movement we chose.

``panning_clip`` slides a window of known width across a still at a known rate,
so the drift the measurement reports can be held to arithmetic rather than to
an opinion about what a pan looks like. That is the whole reason this module
exists: the contact sheet could only ever be argued with.
"""

import pytest

from app.domain import motion as rules
from app.domain.entities import Motion
from app.imaging import motion as measure
from tests.fixtures import CLIP_WIDTH, HAS_FFMPEG, locked_clip, panning_clip

needs_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")


def motion(**kwargs) -> Motion:
    base = dict(frames=12, fps=4.0, drift_x=0.0, drift_y=0.0, step=0.0, step_max=0.0)
    return Motion(**{**base, **kwargs})


# --- measurement against a known pan --------------------------------------


@needs_ffmpeg
@pytest.mark.parametrize("rate", [40, 100])
async def test_a_synthesised_pan_measures_the_distance_it_actually_travelled(rate: int):
    seconds = 3.0
    found = await measure.measure(panning_clip(seconds, rate))
    travelled = rate * seconds / CLIP_WIDTH

    # The strip samples at 4 fps, so n frames give n-1 gaps and the measurement
    # covers (n-1)/n of the clip's travel. That is arithmetic, not error.
    samples = int(seconds * measure.SAMPLE_FPS)
    expected = travelled * (samples - 1) / samples
    assert found.drift_x == pytest.approx(expected, abs=0.06)
    assert found.drift_y == pytest.approx(0.0, abs=0.03)


@needs_ffmpeg
async def test_a_pan_to_the_right_is_reported_as_a_pan_to_the_right():
    """The sign reaches the photographer as a word, so it has to be right."""
    found = rules.read(await measure.measure(panning_clip(3.0, 100)))
    assert found.move == rules.PAN
    assert "right" in found.fact


@needs_ffmpeg
async def test_a_held_frame_measures_as_locked_off():
    found = await measure.measure(locked_clip(3.0))
    assert found.drift_x == 0.0 and found.drift_y == 0.0
    assert found.still_share == 1.0
    assert rules.read(found).move == rules.STATIC_TRIPOD


@needs_ffmpeg
async def test_a_clip_too_short_to_compare_measures_nothing():
    assert await measure.measure(b"not a video at all") is None


# --- classification -------------------------------------------------------


def test_a_locked_frame_supports_the_tripod_and_rules_out_every_move():
    found = rules.read(motion(still_share=0.95, drift_x=0.01))
    assert found.move == rules.STATIC_TRIPOD
    assert found.contradicts == rules.SETTLED - {rules.STATIC_TRIPOD}
    assert "locked" in found.fact


def test_a_steady_sideways_drift_is_a_pan_and_not_a_tilt():
    found = rules.read(motion(drift_x=0.9, drift_y=0.05, step=0.08, step_max=0.1))
    assert found.move == rules.PAN
    assert rules.TILT in found.contradicts
    assert rules.STATIC_TRIPOD in found.contradicts


def test_a_steady_vertical_drift_is_a_tilt_and_not_a_pan():
    found = rules.read(motion(drift_x=0.05, drift_y=0.9, step=0.08, step_max=0.1))
    assert found.move == rules.TILT
    assert rules.PAN in found.contradicts


def test_one_step_big_enough_to_smear_is_a_whip_pan_not_a_fast_pan():
    found = rules.read(motion(drift_x=2.4, step=0.18, step_max=0.63))
    assert found.move == rules.WHIP_PAN
    assert rules.PAN in found.supports
    assert "smear" in found.fact


def test_a_diagonal_drift_is_named_as_neither():
    found = rules.read(motion(drift_x=0.6, drift_y=0.6, step=0.05, step_max=0.1))
    assert found.move == ""
    assert "diagonal" in found.fact


def test_a_wobble_too_small_to_be_a_move_claims_nothing_but_rules_moves_out():
    found = rules.read(motion(drift_x=0.1, still_share=0.2, step=0.02, step_max=0.05))
    assert found.move == ""
    assert found.supports == frozenset()
    assert {rules.PAN, rules.TILT, rules.WHIP_PAN} <= found.contradicts


def test_a_photo_has_no_camera_movement_to_report():
    assert rules.read(None).fact == ""
    assert rules.describe(None) == []


def test_what_translation_cannot_see_is_never_claimed():
    """Rotation, scale and focus are not measured, so the techniques that turn
    on them must appear in neither half of every verdict."""
    unmeasurable = {"orbit", "push_in", "tracking", "rack_focus"}
    for found in (
        rules.read(motion(still_share=0.95)),
        rules.read(motion(drift_x=0.9, step=0.08, step_max=0.1)),
        rules.read(motion(drift_x=2.4, step=0.18, step_max=0.63)),
    ):
        assert not (found.supports | found.contradicts) & unmeasurable
        assert (found.supports | found.contradicts) <= rules.SETTLED


def test_the_prompt_lines_say_what_is_ruled_out_and_what_is_not_measured():
    lines = rules.describe(motion(drift_x=0.9, step=0.08, step_max=0.1))
    assert any("rules out" in line for line in lines)
    assert any("rack_focus" in line for line in lines)
