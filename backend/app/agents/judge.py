"""The Judge's model half: feedback text only. Pass/fail is ``domain/judge.py``."""

from google.adk.agents import LlmAgent
from pydantic import BaseModel

from app.agents import prompts
from app.agents.runtime import run_agent
from app.config import settings
from app.domain import judge as rules
from app.domain.entities import Analysis, Quest


class FeedbackOut(BaseModel):
    feedback: str
    tip: str = ""


def judge_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="judge",
        description="Writes the feedback for a rule-decided quest verdict.",
        instruction=prompts.load("judge"),
        output_schema=FeedbackOut,
        output_key="feedback",
    )


def feedback_prompt(
    quest: Quest,
    passed: bool,
    exif_checks: dict[str, rules.Check],
    vision_checks: dict[str, float],
    analysis: Analysis | None,
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
    score = analysis.score if analysis else "-"
    return (
        f"Quest: {quest.title} (technique `{quest.technique_id}`)\n"
        f"Brief:\n{quest.brief}\n\n"
        f"Criteria:\n" + "\n".join(f"- {c}" for c in quest.criteria.text) + "\n\n"
        f"Result: {'PASSED' if passed else 'NOT PASSED'}\n"
        f"Checks:\n{checks}\n\n"
        f"Analyst evidence:\n{seen}\n"
        f"Analyst critique (score {score}/10): {critique}"
    )


async def feedback(
    quest: Quest,
    passed: bool,
    exif_checks: dict[str, rules.Check],
    vision_checks: dict[str, float],
    analysis: Analysis | None,
) -> FeedbackOut:
    return await run_agent(
        judge_agent(),
        prompt=feedback_prompt(quest, passed, exif_checks, vision_checks, analysis),
        schema=FeedbackOut,
        user_id=quest.user_id,
    )
