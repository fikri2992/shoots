"""The scrub lens: evidence on demand for video.

A contact sheet shows a clip at a glance; it does not always separate a
pan from a tracking shot. The Composer can ask for two timestamps; this
lens pulls those exact frames with ffmpeg, compares them, and votes like
any other lens in ``domain/panel.py``. Its reading counts toward agreement
for the camera-move techniques, which were the panel's weakest reads.
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from app.agents import prompts
from app.agents.analyst import EvidenceOut, LensOut
from app.agents.runtime import bytes_part, run_agent
from app.config import settings
from app.domain import taxonomy
from app.domain.entities import Shot


class NoElements(BaseModel):
    """The scrub lens rates nothing; it only votes on techniques."""


class ScrubOut(LensOut):
    techniques: list[EvidenceOut] = Field(default_factory=list)
    elements: NoElements = Field(default_factory=NoElements)


def scrub_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="scrub",
        description="Compares two frames of a clip to confirm the camera move.",
        instruction=prompts.load("scrub"),
        output_schema=ScrubOut,
        output_key="scrub",
    )


def default_times(duration_s: float) -> list[float]:
    """Two frames around the middle, half a second apart, when the Composer
    did not ask for specific moments."""
    mid = max(0.0, duration_s / 2)
    gap = min(0.5, max(0.1, duration_s / 4))
    return [round(max(0.0, mid - gap / 2), 2), round(min(duration_s, mid + gap / 2), 2)]


def prompt_for(shot: Shot, times: list[float]) -> str:
    grid = shot.grid
    catalogue = "\n".join(
        f"- `{t.id}`: {t.cue}" for t in taxonomy.TECHNIQUES if t.family is taxonomy.Family.VIDEO
    )
    stamps = ", ".join(f"Image {i + 1} at {t:.2f} s" for i, t in enumerate(times))
    return (
        f"Grid: {grid.cols} columns x {grid.rows} rows "
        f"(cells A1 to {chr(ord('A') + grid.cols - 1)}{grid.rows}).\n"
        f"Frames: {stamps}.\n\n"
        f"Video technique catalogue:\n{catalogue}"
    )


async def read(shot: Shot, frames: list[tuple[float, bytes]]) -> ScrubOut:
    """``frames``: (seconds, gridded PNG) pairs, in time order."""
    return await run_agent(
        scrub_agent(),
        prompt=prompt_for(shot, [t for t, _ in frames]),
        images=[bytes_part(png, "image/png") for _, png in frames],
        schema=ScrubOut,
        user_id=shot.user_id,
    )
