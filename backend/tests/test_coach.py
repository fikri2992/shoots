"""The Coach's pure halves: the briefing and the server-message translation.
The Live session itself is checked by scripts/check_coach.py."""

from google.genai import types

from app.agents import coach
from app.api.live import _append
from app.domain.entities import (
    Analysis,
    Composition,
    Exif,
    GridSpec,
    Move,
    Shot,
    ShotKind,
    TechniqueEvidence,
)


def shot() -> Shot:
    return Shot(
        id="shot_1",
        user_id="u1",
        drive_file_id="f1",
        filename="bike.jpg",
        kind=ShotKind.PHOTO,
        mime_type="image/jpeg",
        exif=Exif(exposure_time_s=1 / 30, f_number=5.6, iso=200, focal_length_35mm=50),
        grid=GridSpec(cols=8, rows=6, width=1600, height=1200),
    )


def test_briefing_speaks_in_cells_and_technique_ids():
    analysis = Analysis(
        shot_id="shot_1",
        user_id="u1",
        model="m",
        techniques=[
            TechniqueEvidence(
                technique_id="panning", confidence=0.9, cells=["C3", "D3"], note="blur"
            )
        ],
        composition=Composition(
            subject_cells=["C3", "D3"],
            horizon_row=4,
            moves=[Move(what="rider", from_cells=["C3"], to_cells=["E3"], reason="lead room")],
        ),
        critique="Tight on the left.",
        score=6,
    )
    text = coach.briefing(shot(), analysis, None)
    assert "A1 to H6" in text
    assert "panning (90%) at C3 D3" in text
    assert "rider: C3 -> E3" in text
    assert "1/30" in text and "f/5.6" in text
    assert "Tight on the left." in text


def test_briefing_without_analysis_says_so():
    text = coach.briefing(shot(), None, None)
    assert "has not read this Shot" in text


def test_events_from_server_message():
    message = types.LiveServerMessage(
        server_content=types.LiveServerContent(
            model_turn=types.Content(
                parts=[
                    types.Part(
                        inline_data=types.Blob(data=b"\x00\x01", mime_type="audio/pcm;rate=24000")
                    ),
                    types.Part(text="ignored"),
                ]
            ),
            output_transcription=types.Transcription(text="The lamp "),
            turn_complete=True,
        )
    )
    kinds = [e.kind for e in coach.events_from(message)]
    assert kinds == ["audio", "transcript", "turn_complete"]
    assert coach.events_from(types.LiveServerMessage()) == []
    interrupted = types.LiveServerMessage(server_content=types.LiveServerContent(interrupted=True))
    assert [e.kind for e in coach.events_from(interrupted)] == ["interrupted"]


def test_transcript_fragments_stitch_per_speaker():
    lines: list[dict] = []
    _append(lines, "model", "The lamp ")
    _append(lines, "model", "at C2.")
    _append(lines, "user", "Move it?")
    assert lines == [
        {"role": "model", "text": "The lamp at C2."},
        {"role": "user", "text": "Move it?"},
    ]
