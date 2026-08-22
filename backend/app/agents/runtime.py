"""Shared ADK plumbing: run an agent over image(s) and get validated pydantic back.

Every agent in the pipeline goes through here, so the image-passing and
structured-output conventions live in exactly one place.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    state: dict[str, Any] | None = None,
) -> T:
    """Invoke ``agent`` with text + images, returning its structured output.
    ``state`` seeds session state for ``{key}`` templates in the instruction.

    Raises ``RuntimeError`` if the agent produced no parsable final response —
    callers decide whether that is fatal or a dismissable suspect.
    """
    parts: list[types.Part] = [types.Part(text=prompt), *(images or [])]
    message = types.Content(role="user", parts=parts)

    async def attempt() -> T:
        # A fresh runner and session per attempt: a retry after a partial failure
        # must not inherit half-written state from the call that failed.
        runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
        session = await runner.session_service.create_session(
            app_name=APP_NAME, user_id=user_id, state=dict(state or {})
        )

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


@dataclass
class WorkflowResult:
    """What a workflow left in session state, typed, plus who took how long."""

    outputs: dict[str, Any] = field(default_factory=dict)
    latency: dict[str, float] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


async def run_workflow(
    agent: BaseAgent,
    *,
    prompt: str,
    images: list[types.Part] | None = None,
    state: dict[str, Any] | None = None,
    outputs: dict[str, type[BaseModel]],
    user_id: str = "system",
    timeout: float | None = None,
) -> WorkflowResult:
    """Run a workflow agent (Sequential/Parallel/Loop) and collect its
    sub-agents' ``output_key`` values from session state, validated against
    ``outputs``. A sub-agent whose output is missing or malformed is reported
    in ``errors`` rather than failing the run: the caller decides on quorum.
    """
    parts: list[types.Part] = [types.Part(text=prompt), *(images or [])]
    message = types.Content(role="user", parts=parts)
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=user_id, state=dict(state or {})
    )

    started = time.monotonic()
    last_seen: dict[str, float] = {}

    async def drive() -> None:
        async for event in runner.run_async(
            user_id=user_id, session_id=session.id, new_message=message
        ):
            if event.author:
                last_seen[event.author] = time.monotonic() - started

    if timeout:
        await asyncio.wait_for(drive(), timeout)
    else:
        await drive()

    stored = await runner.session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session.id
    )
    state_out = dict(stored.state) if stored else {}

    result = WorkflowResult(latency=last_seen)
    for key, schema in outputs.items():
        raw = state_out.get(key)
        if raw is None:
            result.errors[key] = "no output"
            continue
        try:
            data = _loads(raw) if isinstance(raw, str) else raw
            result.outputs[key] = schema.model_validate(data)
        except Exception as error:  # noqa: BLE001 — reported, quorum decides
            result.errors[key] = f"{type(error).__name__}: {str(error)[:160]}"
    return result


def _loads(text: str) -> dict:
    """Tolerate fenced JSON, which models emit even when told not to."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        cleaned = cleaned.removeprefix("json").strip()
    return json.loads(cleaned)
