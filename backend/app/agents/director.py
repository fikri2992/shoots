"""The Director's model half: a storyboard from the experiment, then Veo.

Two calls, each replaceable: Gemini writes the generation prompt
(structured, via ADK), Veo renders the clip with its own ambient sound.
``Generators`` is the seam: production uses ``vertex_generators()``; tests
hand in functions that return real bytes.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from google import genai
from google.adk.agents import LlmAgent
from google.genai import types
from pydantic import BaseModel, Field

from app.agents import prompts
from app.agents.retry import with_retry
from app.agents.runtime import run_agent
from app.config import settings
from app.domain.entities import Experiment
from app.domain.taxonomy import Technique

logger = logging.getLogger(__name__)


class Storyboard(BaseModel):
    video_prompt: str = Field(min_length=20)


@dataclass
class Generators:
    storyboard: Callable[[Technique, Experiment], Awaitable[Storyboard]]
    clip: Callable[[str], Awaitable[bytes]]


# --- storyboard (Gemini, structured) ---------------------------------------


def director_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="director",
        description="Writes the Veo prompt for an experiment's reference clip.",
        instruction=prompts.load("director"),
        output_schema=Storyboard,
        output_key="storyboard",
    )


def storyboard_prompt(technique: Technique, experiment: Experiment) -> str:
    criteria = "\n".join(f"- {c}" for c in experiment.criteria.text) or "- (none)"
    return (
        f"Technique: {technique.name} ({technique.family.value}, level {technique.level})\n"
        f"Recognised by: {technique.cue}\n\n"
        f"Experiment: {experiment.title}\n"
        f"Brief:\n{experiment.brief}\n\n"
        f"Criteria:\n{criteria}\n\n"
        f"Clip length: {settings.clip_seconds} seconds, vertical {settings.clip_aspect}."
    )


async def storyboard(technique: Technique, experiment: Experiment) -> Storyboard:
    return await run_agent(
        director_agent(),
        prompt=storyboard_prompt(technique, experiment),
        schema=Storyboard,
        user_id=experiment.user_id,
    )


# --- clip (Veo, long-running) ------------------------------------------------


async def generate_clip(prompt: str) -> bytes:
    """One vertical clip with ambient audio, bytes inline. Polls to completion."""
    client = genai.Client(
        vertexai=True, project=settings.gcp_project, location=settings.media_location
    )

    async def attempt() -> bytes:
        operation = await client.aio.models.generate_videos(
            model=settings.model_video,
            source=types.GenerateVideosSource(prompt=prompt),
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=settings.clip_seconds,
                aspect_ratio=settings.clip_aspect,
                resolution=settings.clip_resolution,
                generate_audio=True,
                person_generation="allow_adult",
            ),
        )
        started = time.monotonic()
        while not operation.done:
            if time.monotonic() - started > settings.generate_timeout_seconds:
                raise TimeoutError(f"veo operation {operation.name} still running")
            await asyncio.sleep(settings.generate_poll_seconds)
            operation = await client.aio.operations.get(operation)
        if operation.error:
            raise RuntimeError(f"veo failed: {operation.error}")
        videos = (operation.response and operation.response.generated_videos) or []
        if not videos or not videos[0].video or not videos[0].video.video_bytes:
            raise RuntimeError("veo returned no video bytes")
        return videos[0].video.video_bytes

    return await with_retry(attempt)


def vertex_generators() -> Generators:
    return Generators(storyboard=storyboard, clip=generate_clip)
