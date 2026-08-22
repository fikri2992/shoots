"""The model boundary: whatever the model says, only grid cells and catalogue
ids survive. Pure, no model."""

from PIL import Image

from app.agents.analyst import (
    AnalystOutput,
    CompositionOut,
    EvidenceOut,
    MoveOut,
    catalogue_text,
    facts_text,
    prompt_for,
    validate,
)
from app.domain.entities import Exif, GridSpec, Shot, ShotKind, VideoMeta
from app.imaging.overlay import render_overlay

PHOTO = Shot(
    id="s1",
    user_id="u1",
    kind=ShotKind.PHOTO,
    drive_file_id="f",
    filename="a.jpg",
    mime_type="image/jpeg",
    grid=GridSpec(cols=8, rows=8, width=1024, height=1024),
    exif=Exif(exposure_time_s=1 / 30, f_number=5.6, iso=200, focal_length_35mm=50),
)


def test_unknown_and_video_only_ids_are_dropped_and_cells_checked():
    raw = AnalystOutput(
        techniques=[
            EvidenceOut(technique_id="Panning", confidence=0.9, cells=["c4", "Z9", "c4"]),
            EvidenceOut(technique_id="made_up", confidence=0.9),
            EvidenceOut(technique_id="pan", confidence=0.9),  # video-only on a photo
            EvidenceOut(technique_id="panning", confidence=0.5),  # duplicate
        ],
        composition=CompositionOut(
            subject_cells=["D4", "E5", "Q1"],
            horizon_row=12,
            moves=[
                MoveOut(what="subject", from_cells=["D4"], to_cells=["C3"], reason="thirds"),
                MoveOut(what="nothing", from_cells=["Z1"], to_cells=["Z2"], reason="bad cells"),
                MoveOut(what="", from_cells=["A1"], to_cells=["B1"]),
                MoveOut(what="4th", from_cells=["A1"], to_cells=["B1"]),
            ],
        ),
        critique="fine",
        score=7,
    )
    analysis = validate(PHOTO, raw)
    assert [t.technique_id for t in analysis.techniques] == ["panning"]
    assert analysis.techniques[0].cells == ["C4"]
    assert analysis.composition.subject_cells == ["D4", "E5"]
    assert analysis.composition.horizon_row is None
    assert [m.what for m in analysis.composition.moves] == ["subject"]
    assert analysis.score == 7 and analysis.model


def test_prompt_carries_grid_facts_and_catalogue():
    text = prompt_for(PHOTO)
    assert "8 columns x 8 rows" in text and "A1 to H8" in text
    assert "shutter: 1/30 s" in text and "aperture: f/5.6" in text and "50 mm" in text
    assert "`panning`" in text and "`pan`" not in text.replace("`panning`", "")


def test_video_prompt_includes_video_techniques_and_fps():
    video = PHOTO.model_copy(
        update={
            "kind": ShotKind.VIDEO,
            "video": VideoMeta(duration_s=9.3, fps=120, width=1920, height=1080),
        }
    )
    text = prompt_for(video)
    assert "frame rate: 120 fps" in text and "`slow_motion`" in text and "`pan`" in text
    assert "video contact sheet" in text


def test_catalogue_and_facts_helpers():
    assert "`pan`" in catalogue_text(video=True)
    assert "`pan`" not in catalogue_text(video=False)
    assert facts_text(Exif(), None) == "- none available"
    assert "shutter: 2 s" in facts_text(Exif(exposure_time_s=2.0), None)


def test_overlay_draws_without_error_and_changes_pixels():
    raw = AnalystOutput(
        composition=CompositionOut(
            subject_cells=["D4"],
            horizon_row=3,
            suggested_crop_cells=["B2", "G7"],
            moves=[MoveOut(what="subject", from_cells=["D4"], to_cells=["C3"], reason="r")],
        )
    )
    analysis = validate(PHOTO, raw)
    base = Image.new("RGB", (2048, 2048), (30, 30, 30))  # larger than the gridded frame
    out = render_overlay(base, PHOTO.grid, analysis.composition)
    assert out.size == base.size
    assert out.getpixel((1024, 1024)) != (30, 30, 30) or out.getpixel((10, 10)) != (30, 30, 30)
