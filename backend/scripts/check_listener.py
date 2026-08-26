"""Run the Listener on a sample transcript with the real model.

    uv run python scripts/check_listener.py

Prints what it would remember. Nothing is written to the store.
"""

import asyncio
import sys

from app.agents import coach

TRANSCRIPT = [
    {
        "role": "model",
        "text": "The light on the fence is the strongest thing at D2. What do you want to work on?",
    },
    {
        "role": "user",
        "text": "Honestly I only have my phone, no tripod or anything. "
        "I shoot on my lunch break near the office.",
    },
    {
        "role": "model",
        "text": "Then skip the long exposures. Try panning the scooters at F4 with a slow shutter.",
    },
    {
        "role": "user",
        "text": "Makes sense. I don't really like shooting people though, I prefer buildings.",
    },
    {"role": "model", "text": "Noted. Architecture gives you lines; use them."},
]


async def main() -> None:
    heard = await coach.listen(TRANSCRIPT, "check")
    for fact in heard.facts:
        print(f"{fact.kind.value}: {fact.value} <- {fact.quote}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    asyncio.run(main())
