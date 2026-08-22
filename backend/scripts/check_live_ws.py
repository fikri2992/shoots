"""Drive /api/live/{shot_id} end to end with a typed question.

    uv run python scripts/check_live_ws.py [shot_id]

Signs a session cookie the way the app does, opens the WebSocket through
Starlette's test client (real app wiring, real Live session), sends one
typed question, collects the audio and transcript, and confirms the coach
event was recorded. No microphone involved; the phone path adds only PCM
frames on the same socket.
"""

import asyncio
import base64
import json
import sys
import time
import wave

from itsdangerous import TimestampSigner
from starlette.testclient import TestClient

from app.api.auth import SESSION_USER_KEY
from app.api.main import app
from app.config import settings
from app.infra import repository as repo
from app.infra.storage import GRIDDED
from app.infra.store import FileStore

QUESTION = "I only have my phone here, no tripod. Give me something else to shoot right where I am."


def session_cookie(user: dict) -> str:
    payload = base64.b64encode(json.dumps({SESSION_USER_KEY: user}).encode())
    return TimestampSigner(settings.session_secret).sign(payload).decode()


async def pick(shot_id: str | None) -> tuple[dict, str]:
    store = FileStore(settings.blob_root + "/store.json")
    users = await repo.list_users(store)
    if not users:
        raise SystemExit("no users in the store; sign in to the dev server first")
    user = users[0]
    shots = await repo.list_shots(store, user.id)
    shot = next((s for s in shots if s.id == shot_id), None) if shot_id else None
    if shot is None:
        shot = next(s for s in shots if s.blobs.get(GRIDDED))
    return {"id": user.id, "email": user.email, "name": user.name}, shot.id


def main(shot_id: str | None) -> None:
    user, shot_id = asyncio.run(pick(shot_id))
    client = TestClient(app)
    client.cookies.set("session", session_cookie(user))

    audio = bytearray()
    lines: list[dict] = []
    started = time.monotonic()
    with client.websocket_connect(f"/api/live/{shot_id}") as socket:
        asked = False
        turns = 0
        issued = False
        while turns < 4 and not issued and time.monotonic() - started < 90:
            message = socket.receive()
            if message.get("bytes"):
                audio += message["bytes"]
                continue
            if not message.get("text"):
                continue
            data = json.loads(message["text"])
            if data["type"] == "tool":
                lines.append({"role": "tool", "text": data["text"]})
                issued = data["name"] == "issue_quest"
                continue
            if data["type"] == "transcript":
                if lines and lines[-1]["role"] == data["role"]:
                    lines[-1]["text"] += data["text"]
                else:
                    lines.append({"role": data["role"], "text": data["text"]})
            elif data["type"] == "turn_complete":
                turns += 1
                print(f"turn {turns} complete at {time.monotonic() - started:.1f}s")
                if not asked:
                    socket.send_text(json.dumps({"type": "text", "text": QUESTION}))
                    asked = True
            elif data["type"] == "error":
                raise SystemExit(f"server error: {data['text']}")
        socket.send_text(json.dumps({"type": "end"}))

    path = settings.blob_root + "/coach_ws_check.wav"
    with wave.open(path, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(24000)
        out.writeframes(bytes(audio))
    print(f"{len(audio) / 2 / 24000:.1f}s of speech -> {path}")
    for line in lines:
        print(f"  {line['role']}: {line['text'].strip()}")

    async def last_event() -> None:
        store = FileStore(settings.blob_root + "/store.json")
        events = await repo.list_events(store, user["id"], limit=3)
        coach = next((e for e in events if e.agent == "coach"), None)
        print("recorded:", coach.detail if coach else "NO coach event")

    asyncio.run(last_event())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
