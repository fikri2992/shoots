"""Open a real Coach session about a stored shot and ask it one question.

    uv run python scripts/check_coach.py [shot_id] ["question"]

Writes the spoken answer to .blobs/coach_check.wav and prints the transcript,
so the voice, the briefing and the cell references can be checked by ear.
"""

import asyncio
import sys
import time
import wave

from google.genai import types

from app.agents import coach
from app.config import settings
from app.infra import repository as repo
from app.infra.storage import GRIDDED, LocalBlobStore
from app.infra.store import FileStore

QUESTION = "Which single cell should I move the subject toward, and why?"


async def main(shot_id: str | None, question: str) -> None:
    store = FileStore(settings.blob_root + "/store.json")
    blobs = LocalBlobStore()
    users = await repo.list_users(store)
    if not users:
        raise SystemExit("no users in the store; sign in to the dev server first")
    shots = await repo.list_shots(store, users[0].id)
    shot = next((s for s in shots if s.id == shot_id), None) if shot_id else None
    if shot is None:
        shot = next(s for s in shots if s.blobs.get(GRIDDED))
    analysis = await repo.find_analysis(store, shot.id)
    image = await blobs.read(shot.blobs[GRIDDED])
    print(f"shot {shot.id} {shot.filename} analysed={analysis is not None}")

    started = time.monotonic()
    audio = bytearray()
    transcript: list[dict] = []
    async with coach.connect() as session:
        await session.send_client_content(
            turns=coach.opening_turn(image, "image/png", coach.briefing(shot, analysis, None)),
            turn_complete=True,
        )
        for turn in range(2):
            async for message in session.receive():
                done = False
                for event in coach.events_from(message):
                    if event.kind == "audio":
                        audio += event.data
                    elif event.kind == "transcript":
                        if transcript and transcript[-1]["role"] == event.role:
                            transcript[-1]["text"] += event.text
                        else:
                            transcript.append({"role": event.role, "text": event.text})
                    elif event.kind == "turn_complete":
                        done = True
                if done:
                    break
            print(f"turn {turn + 1} done at {time.monotonic() - started:.1f}s")
            if turn == 0:
                await session.send_client_content(
                    turns=types.Content(role="user", parts=[types.Part(text=question)]),
                    turn_complete=True,
                )

    path = settings.blob_root + "/coach_check.wav"
    with wave.open(path, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(coach.OUTPUT_RATE)
        out.writeframes(bytes(audio))
    print(f"{len(audio) / 2 / coach.OUTPUT_RATE:.1f}s of speech -> {path}")
    for line in transcript:
        print(f"  {line['role']}: {line['text'].strip()}")


if __name__ == "__main__":
    asyncio.run(
        main(
            sys.argv[1] if len(sys.argv) > 1 else None,
            sys.argv[2] if len(sys.argv) > 2 else QUESTION,
        )
    )
