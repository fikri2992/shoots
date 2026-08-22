"""The Director's model half: a storyboard from the quest, then Veo and Lyria.

Three calls, each replaceable: Gemini writes the two generation prompts
(structured, via ADK), Veo renders the clip, Lyria plays the mood. The
service glues them with ffmpeg. ``Generators`` is the seam: production uses
``vertex_generators()``; tests hand in functions that return real bytes.
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
from app.domain.entities import Quest
from app.domain.taxonomy import Technique

logger = logging.getLogger(__name__)


class Storyboard(BaseModel):
    video_prompt: str = Field(min_length=20)
    music_prompt: str = Field(min_length=10)


@dataclass
class Track:
    data: bytes
    mime_type: str


@dataclass
class Generators:
    storyboard: Callable[[Technique, Quest], Awaitable[Storyboard]]
    clip: Callable[[str], Awaitable[bytes]]
    track: Callable[[str], Awaitable[Track]]


# --- storyboard (Gemini, structured) ---------------------------------------


def director_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="director",
        description="Writes the Veo and Lyria prompts for a quest's reference clip.",
        instruction=prompts.load("director"),
        output_schema=Storyboard,
        output_key="storyboard",
    )


def storyboard_prompt(technique: Technique, quest: Quest) -> str:
    criteria = "\n".join(f"- {c}" for c in quest.criteria.text) or "- (none)"
    return (
        f"Technique: {technique.name} ({technique.family.value}, level {technique.level})\n"
        f"Recognised by: {technique.cue}\n\n"
        f"Quest: {quest.title}\n"
        f"Brief:\n{quest.brief}\n\n"
        f"Criteria:\n{criteria}\n\n"
        f"Clip length: {settings.clip_seconds} seconds, vertical {settings.clip_aspect}."
    )


async def storyboard(technique: Technique, quest: Quest) -> Storyboard:
    return await run_agent(
        director_agent(),
        prompt=storyboard_prompt(technique, quest),
        schema=Storyboard,
        user_id=quest.user_id,
    )


# --- clip (Veo, long-running) ------------------------------------------------


def _media_client(location: str) -> genai.Client:
    return genai.Client(vertexai=True, project=settings.gcp_project, location=location)


async def generate_clip(prompt: str) -> bytes:
    """One silent vertical clip, bytes inline. Polls the operation to completion."""
    client = _media_client(settings.media_location)

    async def attempt() -> bytes:
        operation = await client.aio.models.generate_videos(
            model=settings.model_video,
            source=types.GenerateVideosSource(prompt=prompt),
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=settings.clip_seconds,
                aspect_ratio=settings.clip_aspect,
                resolution=settings.clip_resolution,
                generate_audio=False,
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


# --- track (Lyria) -----------------------------------------------------------


async def generate_track(prompt: str) -> Track:
    """A 30 s instrumental. Lyria always returns a caption part too; we keep the audio."""
    client = _media_client(settings.music_location)

    async def attempt() -> Track:
        response = await client.aio.models.generate_content(
            model=settings.model_music,
            contents=f"Instrumental, no vocals. {prompt}",
            config=types.GenerateContentConfig(response_modalities=["AUDIO", "TEXT"]),
        )
        for candidate in response.candidates or []:
            for part in (candidate.content and candidate.content.parts) or []:
                blob = part.inline_data
                if blob and blob.data and (blob.mime_type or "").startswith("audio/"):
                    return Track(data=blob.data, mime_type=blob.mime_type or "")
        raise RuntimeError("lyria returned no audio part")

    return await with_retry(attempt)


def vertex_generators() -> Generators:
    return Generators(storyboard=storyboard, clip=generate_clip, track=generate_track)
