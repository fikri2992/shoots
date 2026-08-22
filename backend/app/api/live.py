"""Voice review over a WebSocket: phone ↔ this service ↔ Gemini Live.

One socket per session, bound to one shot. The browser sends binary frames
of 16 kHz PCM16 and JSON text frames (``{"type": "text", "text": ...}`` for a
typed question, ``{"type": "end"}`` to hang up). It receives binary frames of
24 kHz PCM16 and JSON frames for transcripts, interruptions and turn ends.
The session is briefed with the gridded frame and the Analyst's read before
the first word, and is logged as one ActivityEvent when it ends.
"""

import asyncio
import contextlib
import json
import logging
import time

from fastapi import APIRouter, WebSocket
from google.genai import types

from app.agents import coach as agent
from app.api.auth import SESSION_USER_KEY
from app.api.deps import get_context
from app.config import settings
from app.infra import repository as repo
from app.infra.storage import GRIDDED, ORIGINAL, SHEET

logger = logging.getLogger(__name__)

router = APIRouter(tags=["live"])

AGENT = "coach"
#: Kept in the event detail so the feed can show what was discussed.
TRANSCRIPT_CHARS = 1500


@router.websocket("/api/live/{shot_id}")
async def live(websocket: WebSocket, shot_id: str):
    user = websocket.session.get(SESSION_USER_KEY)
    if not user:
        await websocket.close(code=4401)
        return
    ctx = get_context()
    shot = await repo.find_shot(ctx.store, shot_id)
    if shot is None or shot.user_id != user["id"]:
        await websocket.close(code=4404)
        return

    analysis = await repo.find_analysis(ctx.store, shot.id)
    quest = None
    if shot.quest_id:
        try:
            quest = await repo.get_quest(ctx.store, shot.quest_id)
        except repo.UnknownEntity:
            quest = None
    key = next((k for k in (GRIDDED, SHEET, ORIGINAL) if shot.blobs.get(k)), None)
    if key is None:
        await websocket.close(code=4409)
        return
    image = await ctx.blobs.read(shot.blobs[key])
    mime = "image/jpeg" if shot.blobs[key].endswith((".jpg", ".jpeg")) else "image/png"

    await websocket.accept()
    started = time.monotonic()
    transcript: list[dict] = []
    turns = 0

    try:
        async with agent.connect() as session:
            await session.send_client_content(
                turns=agent.opening_turn(image, mime, agent.briefing(shot, analysis, quest)),
                turn_complete=True,
            )

            async def inbound() -> None:
                while True:
                    message = await websocket.receive()
                    if message["type"] == "websocket.disconnect":
                        return
                    if message.get("bytes"):
                        await session.send_realtime_input(
                            audio=types.Blob(data=message["bytes"], mime_type=agent.INPUT_MIME)
                        )
                        continue
                    if message.get("text"):
                        data = json.loads(message["text"])
                        if data.get("type") == "end":
                            return
                        if data.get("type") == "text" and data.get("text", "").strip():
                            await session.send_client_content(
                                turns=types.Content(
                                    role="user", parts=[types.Part(text=data["text"].strip())]
                                ),
                                turn_complete=True,
                            )

            async def outbound() -> None:
                nonlocal turns
                while True:
                    async for message in session.receive():
                        for event in agent.events_from(message):
                            if event.kind == "audio":
                                await websocket.send_bytes(event.data)
                                continue
                            if event.kind == "transcript":
                                _append(transcript, event.role, event.text)
                            if event.kind == "turn_complete":
                                turns += 1
                            await websocket.send_text(
                                json.dumps(
                                    {"type": event.kind, "role": event.role, "text": event.text}
                                )
                            )
                    if time.monotonic() - started > settings.live_max_minutes * 60:
                        await websocket.send_text(json.dumps({"type": "timeout"}))
                        return

            tasks = [asyncio.create_task(inbound()), asyncio.create_task(outbound())]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            for task in done:
                if task.exception():
                    raise task.exception()
    except Exception as error:  # noqa: BLE001 — the socket must report, not hang
        logger.exception("coach session failed for %s", shot.id)
        with contextlib.suppress(Exception):
            await websocket.send_text(
                json.dumps({"type": "error", "text": f"{type(error).__name__}: {error}"[:300]})
            )
    finally:
        seconds = round(time.monotonic() - started)
        if transcript:
            text = "\n".join(f"{t['role']}: {t['text']}" for t in transcript)
            await repo.record(
                ctx.store,
                shot.user_id,
                AGENT,
                "session",
                {
                    "seconds": seconds,
                    "turns": turns,
                    "transcript": text[-TRANSCRIPT_CHARS:],
                    "model": settings.model_live,
                },
                shot_id=shot.id,
                quest_id=shot.quest_id,
            )
        with contextlib.suppress(Exception):  # already gone is fine
            await websocket.close()


def _append(transcript: list[dict], role: str, text: str) -> None:
    """Transcripts arrive as fragments; stitch them into one line per speaker turn."""
    if transcript and transcript[-1]["role"] == role:
        transcript[-1]["text"] += text
    else:
        transcript.append({"role": role, "text": text})
