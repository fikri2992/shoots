"""Judge-facing proof must match the workflow and prompt version actually accepted."""

from pathlib import Path

from app.agents import prompts

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_demo_docs_do_not_present_unverified_camera_or_stale_timing_as_proof():
    demo = _read("docs/demo-rehearsal.md")
    proof = _read("docs/submission-proof.md")
    devpost = _read("docs/devpost-story-codex.md")
    combined = "\n".join((demo, proof, devpost))

    for stale in (
        "4+ minutes later",
        "waits for four minutes of inactivity",
        "cloud_run_revision=shoots-00006-mzn",
        "No manual upload",
    ):
        assert stale not in combined

    assert "75 selected Drive Shots" in combined
    assert "physical Camera-to-Shoot workflow remains unaccepted" in combined
    assert "300-Shot workflow passed" not in combined


def test_quality_doc_marks_the_old_report_as_historical_for_the_current_prompt():
    quality = _read("docs/agent-quality.md")
    current = prompts.bundle_version(("technician", "composer", "storyteller", "synthesizer"))

    assert current in quality
    assert "has not completed the real-agent acceptance gate" in quality
    assert "1c738851cdfb" in quality
