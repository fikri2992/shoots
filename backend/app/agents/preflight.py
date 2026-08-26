"""Explicit Companion Ask: visible Criteria checked on a temporary Scene Probe.

One small call on a 640 px preview, answered in a few seconds, so the
photographer can make one supported move while the decision is still open. The
probe creates no Shot; the panel and Judge do the real reading after capture.
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


def bound_response(out: PreflightOut, criteria: list[str]) -> PreflightOut:
    """Restore the declared Criteria and enforce one move after model output.

    The model supplies the visual read and words. Code owns which Criteria were
    asked, whether every one was checked, and the one-move product boundary.
    Missing checks become unresolved rather than silently disappearing.
    """
    unused = list(out.checks)
    ordered: list[CheckOut] = []
    for criterion in criteria:
        exact = next(
            (
                check
                for check in unused
                if check.criterion.strip().casefold() == criterion.casefold()
            ),
            None,
        )
        check = exact or (unused[0] if unused else None)
        if check in unused:
            unused.remove(check)
        ordered.append(
            CheckOut(
                criterion=criterion,
                met=check.met if check else False,
                fix=check.fix.strip() if check and not check.met else "",
            )
        )

    fixes = [check for check in ordered if check.fix]
    if len(fixes) > 1:
        say_words = set(out.say.casefold().split())
        keep = max(fixes, key=lambda check: len(say_words & set(check.fix.casefold().split())))
        for check in fixes:
            if check is not keep:
                check.fix = ""

    ready = bool(ordered) and all(check.met for check in ordered)
    say = out.say.strip()
    if not say:
        move = next((check.fix for check in ordered if check.fix), "")
        say = move or "I cannot verify the visible Criteria from this preview."
    return PreflightOut(checks=ordered, ready=ready, say=say)


async def check(experiment: Experiment, technique: Technique, preview_jpeg: bytes) -> PreflightOut:
    out = await run_agent(
        preflight_agent(),
        prompt=prompt_for(experiment, technique),
        images=[bytes_part(preview_jpeg, "image/jpeg")],
        schema=PreflightOut,
        user_id=experiment.user_id,
    )
    return bound_response(out, experiment.criteria.text)
