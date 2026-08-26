"""The Judge's model half: feedback text only. Pass/fail is ``domain/judge.py``."""

from google.adk.agents import LlmAgent
from pydantic import BaseModel

from app.agents import prompts
from app.agents.analyst import facts_text
from app.agents.runtime import bytes_part, run_agent
from app.config import settings
from app.domain import judge as rules
from app.domain.entities import Analysis, Experiment, Shot


class FeedbackOut(BaseModel):
    feedback: str
    tip: str = ""


def judge_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="judge",
        description="Writes the feedback for a rule-decided experiment verdict.",
        instruction=prompts.load("judge"),
        output_schema=FeedbackOut,
        output_key="feedback",
    )


def feedback_prompt(
    experiment: Experiment,
    criteria_met: bool,
    exif_checks: dict[str, rules.Check],
    vision_checks: dict[str, float],
    analysis: Analysis | None,
    shot: Shot | None = None,
    previous: tuple[Shot, Analysis] | None = None,
) -> str:
    checks = "\n".join(
        f"- {line}"
        for line in rules.describe_checks(exif_checks, vision_checks, settings.judge_min_confidence)
    )
    seen = (
        "\n".join(f"- {t.technique_id} ({t.confidence:.0%}): {t.note}" for t in analysis.techniques)
        if analysis and analysis.techniques
        else "- nothing tagged"
    )
    critique = analysis.critique if analysis else "(no analysis)"
    facts = facts_text(shot.exif, shot.video) if shot else "- none available"
    if previous:
        prev_shot, prev_analysis = previous
        when = prev_shot.captured_at.date().isoformat() if prev_shot.captured_at else "earlier"
        prev_seen = ", ".join(
            f"{t.technique_id} {t.confidence:.0%}" for t in prev_analysis.techniques
        )
        kept = ", one they marked a keeper" if prev_shot.kept_at else ""
        previous_text = (
            f"Image 2 is their own earlier Shot using this Technique ({when}{kept}; "
            f"seen: {prev_seen or '-'}). Observations then:\n"
            + "\n".join(f"- {o}" for o in prev_analysis.observations[:6])
        )
    else:
        previous_text = "No earlier shot of this technique to compare with; say so in one clause."
    observations = "\n".join(f"- {o}" for o in analysis.observations[:8]) if analysis else "- none"
    # Arithmetic, not opinion: the model may state these figures as fact.
    found = (
        "\n".join(f"- {f.what} ({f.why})" for f in analysis.findings)
        if analysis and analysis.findings
        else "- the arithmetic found nothing wrong"
    )
    return (
        f"Experiment: {experiment.title} (technique `{experiment.technique_id}`)\n"
        f"Brief:\n{experiment.brief}\n\n"
        f"Criteria:\n" + "\n".join(f"- {c}" for c in experiment.criteria.text) + "\n\n"
        f"Result: {'CRITERIA MET' if criteria_met else 'CRITERIA NOT MET'}\n"
        f"Checks:\n{checks}\n\n"
        f"Analyst evidence:\n{seen}\n"
        f"Analyst observations (Image 1):\n{observations}\n"
        f"Analyst critique: {critique}\n"
        f"Findings, computed from the numbers (checkable; state them plainly):\n{found}\n\n"
        f"Camera facts:\n{facts}\n\n"
        f"{previous_text}"
    )


async def feedback(
    experiment: Experiment,
    criteria_met: bool,
    exif_checks: dict[str, rules.Check],
    vision_checks: dict[str, float],
    analysis: Analysis | None,
    shot: Shot | None = None,
    previous: tuple[Shot, Analysis] | None = None,
    images: list[bytes] | None = None,
) -> FeedbackOut:
    """``images``: the current gridded Shot, then the earlier reference, as PNG bytes."""
    return await run_agent(
        judge_agent(),
        prompt=feedback_prompt(
            experiment, criteria_met, exif_checks, vision_checks, analysis, shot, previous
        ),
        images=[bytes_part(data, "image/png") for data in (images or [])],
        schema=FeedbackOut,
        user_id=experiment.user_id,
    )
