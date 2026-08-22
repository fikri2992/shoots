"""Shared ADK plumbing: run an agent over image(s) and get validated pydantic back.

Every agent in the pipeline goes through here, so the image-passing and
structured-output conventions live in exactly one place.
"""

import json
import logging
from pathlib import Path

from google.adk.agents import BaseAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel

from app.agents.retry import with_retry

APP_NAME = "shoots"

logger = logging.getLogger(__name__)

_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def image_part(path: str | Path) -> types.Part:
    """Read an image off disk into a Gemini inline part."""
    path = Path(path)
    mime = _MIME_BY_SUFFIX.get(path.suffix.lower())
    if mime is None:
        raise ValueError(f"unsupported image type: {path.suffix}")
    return types.Part.from_bytes(data=path.read_bytes(), mime_type=mime)


def bytes_part(data: bytes, mime_type: str = "image/png") -> types.Part:
    """For images we generate in-memory (grid overlays, contact sheets, crops)."""
    return types.Part.from_bytes(data=data, mime_type=mime_type)


async def run_agent[T: BaseModel](
    agent: BaseAgent,
    *,
    prompt: str,
    images: list[types.Part] | None = None,
    schema: type[T],
    user_id: str = "system",
) -> T:
    """Invoke ``agent`` with text + images, returning its structured output.

    Raises ``RuntimeError`` if the agent produced no parsable final response —
    callers decide whether that is fatal or a dismissable suspect.
    """
    parts: list[types.Part] = [types.Part(text=prompt), *(images or [])]
    message = types.Content(role="user", parts=parts)

    async def attempt() -> T:
        # A fresh runner and session per attempt: a retry after a partial failure
        # must not inherit half-written state from the call that failed.
        runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
        session = await runner.session_service.create_session(app_name=APP_NAME, user_id=user_id)

        final_text: str | None = None
        async for event in runner.run_async(
            user_id=user_id, session_id=session.id, new_message=message
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(part.text or "" for part in event.content.parts)

        if not final_text:
            raise RuntimeError(f"{agent.name} returned no final response")

        return schema.model_validate(_loads(final_text))

    def note(attempt_number: int, delay: float, error: BaseException) -> None:
        logger.warning(
            "%s attempt %d failed (%s); retrying in %.1fs",
            agent.name,
            attempt_number,
            str(error)[:120],
            delay,
        )

    return await with_retry(attempt, on_retry=note)


def _loads(text: str) -> dict:
    """Tolerate fenced JSON, which models emit even when told not to."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        cleaned = cleaned.removeprefix("json").strip()
    return json.loads(cleaned)
