"""The model boundary: whatever the lenses say, only grid cells and catalogue
ids survive, and the panel's vote decides what counts. Pure, no model."""

from app.agents.analyst import (
    ComposerOut,
    CompositionOut,
    EvidenceOut,
    MoveOut,
    PanelResult,
    StorytellerOut,
    SynthesisOut,
    TechnicianOut,
    catalogue_text,
    facts_text,
    prompt_for,
    state_for,
    validate,
)
from app.domain.entities import Exif, GridSpec, Shot, ShotKind, VideoMeta

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


def panel_result() -> PanelResult:
    technician = TechnicianOut(
        observations=["The rider at D4 is sharp.", "The fence at A6-H6 is streaked."],
        techniques=[
            EvidenceOut(technique_id="Panning", confidence=0.9, cells=["c4", "Z9", "c4"]),
            EvidenceOut(technique_id="made_up", confidence=0.9),
            EvidenceOut(technique_id="pan", confidence=0.9),  # video-only on a photo
            EvidenceOut(technique_id="deep_dof", confidence=0.5),  # alone, below owner bar
        ],
        elements={"technical": 7},
        note="Shutter suits the pan.",
    )
    composer = ComposerOut(
        observations=["The rider at D4 is sharp.", "Horizon along row 6."],
        techniques=[
            EvidenceOut(technique_id="panning", confidence=0.7, cells=["D4"]),
            EvidenceOut(technique_id="rule_of_thirds", confidence=0.8, cells=["D4"]),
        ],
        elements={"composition": 6, "lighting": 10},
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
    )
    storyteller = StorytellerOut(
        observations=["A rider on a red bike at D4."],
        techniques=[EvidenceOut(technique_id="single_accent", confidence=0.8, cells=["D4"])],
        elements={"impact": 8, "story": 6},
    )
    return PanelResult(
        reads={"technician": technician, "composer": composer, "storyteller": storyteller},
        synthesis=SynthesisOut(critique="The pan works; give the rider room at C3."),
        latency={"technician": 4.2, "composer": 5.1, "storyteller": 3.9},
    )


def test_vote_cells_and_catalogue_are_enforced():
    analysis = validate(PHOTO, panel_result())
    by_id = {t.technique_id: t for t in analysis.techniques}
    # panning: two lenses agreed; confidence is their mean; cells are the union, checked
    assert by_id["panning"].agreement == 2 and by_id["panning"].lenses == ["technician", "composer"]
    assert abs(by_id["panning"].confidence - 0.8) < 1e-6
    assert by_id["panning"].cells == ["C4", "D4"]
    # owner alone at >= 0.75 counts; owner alone at 0.5 does not; unknown/video ids never
    assert by_id["rule_of_thirds"].agreement == 1 and by_id["single_accent"].agreement == 1
    assert "deep_dof" not in by_id and "made_up" not in by_id and "pan" not in by_id
    # elements: only each lens's own, clamped, then the weighted overall computed here
    assert analysis.elements == {
        "impact": 8,
        "composition": 6,
        "lighting": 10,
        "technical": 7,
        "story": 6,
    }
    assert analysis.score == 8  # 0.3*8 + 0.25*6 + 0.2*10 + 0.15*7 + 0.1*6 = 7.55
    assert analysis.composition.subject_cells == ["D4", "E5"]
    assert analysis.composition.horizon_row is None
    assert [m.what for m in analysis.composition.moves] == ["subject"]
    assert (
        analysis.observations[0] == "The rider at D4 is sharp." and len(analysis.observations) == 4
    )
    assert analysis.critique.startswith("The pan works")
    assert analysis.panel == {"technician": 4.2, "composer": 5.1, "storyteller": 3.9}


def test_missing_synthesis_falls_back_to_lens_notes_and_two_lenses_suffice():
    result = panel_result()
    result.synthesis = None
    del result.reads["storyteller"]
    analysis = validate(PHOTO, result)
    assert "Shutter suits the pan." in analysis.critique
    assert "impact" not in analysis.elements and analysis.score >= 1


def test_prompt_carries_grid_and_catalogue_and_state_carries_facts():
    text = prompt_for(PHOTO)
    assert "8 columns x 8 rows" in text and "A1 to H8" in text
    assert "`panning`" in text and "`pan`" not in text.replace("`panning`", "")
    state = state_for(PHOTO)
    assert "shutter: 1/30 s" in state["facts"] and "aperture: f/5.6" in state["facts"]
    assert "- 8: merit" in state["anchors"]


def test_video_prompt_includes_video_techniques_and_fps():
    video = PHOTO.model_copy(
        update={
            "kind": ShotKind.VIDEO,
            "video": VideoMeta(duration_s=9.3, fps=120, width=1920, height=1080),
        }
    )
    assert "`slow_motion`" in prompt_for(video) and "`pan`" in prompt_for(video)
    assert "frame rate: 120 fps" in state_for(video)["facts"]
    assert "video contact sheet" in prompt_for(video)


def test_catalogue_and_facts_helpers():
    assert "`orbit`" in catalogue_text(video=True) and "`orbit`" not in catalogue_text(video=False)
    assert facts_text(Exif(), None) == "- none available"
