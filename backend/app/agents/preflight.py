"""Pre-flight: the experiment's criteria checked on a preview, before upload.

One small call on a 640 px preview, answered in a few seconds, so the
photographer reshoots on the spot instead of learning from a verdict at
home. It checks only the experiment's SEEN criteria; the panel and the Judge do
the real reading once the frame is sent.
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from app.agents import prompts
from app.agents.runtime import bytes_part, run_agent
from app.config import settings
from app.domain.entities import Experiment
from app.domain.taxonomy import Technique

PREVIEW_EDGE = 640


class CheckOut(BaseModel):
    criterion: str
    met: bool
    fix: str = ""


class PreflightOut(BaseModel):
    checks: list[CheckOut] = Field(default_factory=list)
    ready: bool = False
    say: str = ""


def preflight_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="preflight",
        description="Checks a preview against the experiment criteria before upload.",
        instruction=prompts.load("preflight"),
        output_schema=PreflightOut,
        output_key="preflight",
    )


def prompt_for(experiment: Experiment, technique: Technique) -> str:
    criteria = "\n".join(f"- {c}" for c in experiment.criteria.text) or "- (none)"
    return (
        f"Experiment: {experiment.title} (technique {technique.name}: {technique.cue})\n"
        f"Criteria to check on the preview:\n{criteria}"
    )


async def check(experiment: Experiment, technique: Technique, preview_jpeg: bytes) -> PreflightOut:
    return await run_agent(
        preflight_agent(),
        prompt=prompt_for(experiment, technique),
        images=[bytes_part(preview_jpeg, "image/jpeg")],
        schema=PreflightOut,
        user_id=experiment.user_id,
    )
