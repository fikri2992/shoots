"""The Journey Update's model half: one paragraph, from figures only.

Everything that decides *whether* to write and *what may be said* is
arithmetic in ``domain/tendency.py`` and ``domain/skills.py``. This agent
turns that evidence into the sentences the photographer reads, and it is the
only part of the update a model touches. It sees no photograph — it has no
reason to: the claim is about a body of work, not about any one frame.
"""

import logging

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from app.agents import prompts
from app.agents.runtime import run_agent
from app.config import settings

logger = logging.getLogger(__name__)


class JourneyOut(BaseModel):
    body: str = Field(description="One paragraph, three to five sentences, under 90 words.")


def journey_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="journey",
        description="Writes the photographer's Journey Update from measured evidence.",
        instruction=prompts.load("journey"),
        output_schema=JourneyOut,
        output_key="journey",
    )


async def write(evidence: list[str], previous: str, taste_is_known: bool) -> str:
    """The paragraph, or empty if the model gave nothing usable.

    A failure here costs the sentences, not the update: the evidence is
    already computed and stored, and the page can render the figures on their
    own. The paragraph is the nicest way to read them, never the only way.
    """
    try:
        out = await run_agent(
            journey_agent(),
            schema=JourneyOut,
            prompt="Write this photographer's Journey Update.",
            state={
                "evidence": "\n".join(f"- {line}" for line in evidence),
                "previous": previous or "(nothing written yet)",
                "taste": "known" if taste_is_known else "unknown",
            },
        )
    except Exception:  # noqa: BLE001 — the figures stand without the prose
        logger.exception("journey writer failed")
        return ""
    return (out.body or "").strip()[:800]
