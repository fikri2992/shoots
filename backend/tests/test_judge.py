"""Judge rules: hard evidence first, vision second, missing EXIF handled honestly."""

from datetime import UTC, datetime, timedelta

from app.domain import judge
from app.domain.entities import (
    Analysis,
    Criteria,
    Exif,
    ExifRule,
    Experiment,
    Shot,
    ShotKind,
    TechniqueEvidence,
)

T = 0.6


def analysis_with(*evidence: tuple[str, float]) -> Analysis:
    return Analysis(
        shot_id="s",
        user_id="u",
        model="m",
        techniques=[TechniqueEvidence(technique_id=t, confidence=c) for t, c in evidence],
    )


def test_panning_bounds_pass_and_fail_on_shutter():
    rule = ExifRule(shutter_min_s=1 / 60, shutter_max_s=1 / 10)
    assert judge.check_exif(rule, Exif(exposure_time_s=1 / 30)) == {
        "shutter_min_s": True,
        "shutter_max_s": True,
    }
    assert judge.check_exif(rule, Exif(exposure_time_s=1 / 500))["shutter_min_s"] is False
    assert judge.check_exif(rule, Exif(exposure_time_s=1.0))["shutter_max_s"] is False


def test_every_bound_kind_resolves():
    rule = ExifRule(
        aperture_max=2.8,
        aperture_min=1.4,
        iso_min=100,
        iso_max=6400,
        focal_min_mm=24,
        focal_max_mm=200,
        flash=True,
    )
    exif = Exif(f_number=1.8, iso=800, focal_length_35mm=50, flash_fired=True)
    assert all(v is True for v in judge.check_exif(rule, exif).values())
    worse = Exif(f_number=4.0, iso=50, focal_length_mm=300, flash_fired=False)
    checks = judge.check_exif(rule, worse)
    assert checks["aperture_max"] is False and checks["iso_min"] is False
    assert checks["focal_max_mm"] is False and checks["flash"] is False


def test_missing_tags_are_none_not_false():
    rule = ExifRule(shutter_min_s=1.0, aperture_min=8)
    checks = judge.check_exif(rule, Exif())
    assert checks == {"shutter_min_s": None, "aperture_min": None}


def test_passes_hard_first_then_vision():
    assert judge.passes({"shutter_min_s": True}, {"long_exposure": 0.9}, T)
    assert not judge.passes({"shutter_min_s": False}, {"long_exposure": 0.99}, T)
    assert not judge.passes({"shutter_min_s": True}, {"long_exposure": 0.5}, T)
    # Bounds exist but EXIF is stripped: vision alone cannot pass it.
    assert not judge.passes({"shutter_min_s": None}, {"long_exposure": 0.9}, T)
    # One checkable bound true, another unknown: still passes.
    assert judge.passes({"shutter_min_s": True, "iso_min": None}, {"long_exposure": 0.9}, T)
    # No bounds at all: vision decides.
    assert judge.passes({}, {"golden_hour": 0.7}, T)
    assert not judge.passes({}, {"golden_hour": 0.59}, T)


def test_evaluate_uses_analysis_confidence():
    criteria = Criteria(exif=ExifRule(shutter_min_s=1.0), vision=["long_exposure"])
    ok, exif_checks, vision = judge.evaluate(
        criteria, Exif(exposure_time_s=2.5), analysis_with(("long_exposure", 0.95)), T
    )
    assert ok and vision == {"long_exposure": 0.95}
    ok, _, vision = judge.evaluate(criteria, Exif(exposure_time_s=2.5), None, T)
    assert not ok and vision == {"long_exposure": 0.0}


def test_submission_rule():
    issued = datetime(2026, 8, 22, 12, tzinfo=UTC)
    experiment = Experiment(
        id="q1",
        user_id="u",
        technique_id="golden_hour",
        title="t",
        brief="b",
        why_now="w",
        criteria=Criteria(),
        issued_at=issued,
    )

    def shot(ingested: datetime, experiment_id: str = "") -> Shot:
        return Shot(
            id="s",
            user_id="u",
            kind=ShotKind.PHOTO,
            drive_file_id="f",
            filename="a.jpg",
            mime_type="image/jpeg",
            ingested_at=ingested,
            experiment_id=experiment_id,
        )

    assert judge.is_submission(shot(issued + timedelta(hours=1)), experiment)
    assert not judge.is_submission(shot(issued - timedelta(hours=1)), experiment)
    assert judge.is_submission(shot(issued - timedelta(days=9), experiment_id="q1"), experiment)
    other = shot(issued + timedelta(hours=1), experiment_id="other")
    assert not judge.is_submission(other, experiment)


def test_describe_checks_is_plain():
    lines = judge.describe_checks({"shutter_min_s": False, "iso_min": None}, {"panning": 0.7}, T)
    assert lines == [
        "shutter min s: not met",
        "iso min: could not check (no EXIF)",
        "panning: seen (70%)",
    ]


def test_computed_findings_reach_the_feedback_prompt():
    """The Judge writes; the arithmetic decides. A figure the model can quote is
    the difference between "work on your technique" and "1/25 s at 85 mm"."""
    from app.agents.judge import feedback_prompt
    from app.domain.entities import Finding

    experiment = Experiment(
        id="q1",
        user_id="u1",
        technique_id="panning",
        title="Panning",
        brief="Follow the rider.",
        why_now="Your last three are frozen.",
        criteria=Criteria(text=["1/30 s or slower"]),
    )
    analysis = Analysis(shot_id="s1", user_id="u1", model="m")
    prompt = feedback_prompt(experiment, True, {}, {}, analysis)
    assert "the arithmetic found nothing wrong" in prompt

    analysis.findings = [
        Finding(finding_id="camera_shake", what="That softness is shake.", why="1/25 s at 85 mm")
    ]
    text = feedback_prompt(experiment, False, {}, {}, analysis)
    assert "That softness is shake. (1/25 s at 85 mm)" in text
