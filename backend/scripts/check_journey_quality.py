"""Run the real Journey writer against evidence-bound overclaim cases.

    uv run python scripts/check_journey_quality.py

This is a model quality check, not a mocked test. It exits non-zero if the writer
returns no usable paragraph, exceeds its copy budget, or turns recurrence into
repeatability, mastery, improvement, or causation.
"""

from __future__ import annotations

import asyncio
import json
import sys

from app.agents import journey, prompts
from app.config import settings

FORBIDDEN = (
    "repeatable",
    "repeatably",
    "reliable",
    "reliably",
    "mastered",
    "mastery",
    "improved",
    "improving",
    "got better",
    "better photographer",
    "under control",
    "because of the experiment",
    "after trying it",
    "it worked",
    "thanks to",
)

CASES = (
    {
        "id": "recurrence_is_not_control",
        "taste": False,
        "previous": "",
        "evidence": [
            "18 Shots read in total.",
            "placement: centred 12, off centre 6 (of 18 readable) — barely varies, "
            "67% of them centred",
            "scenes: 18 Shots across 7 Scenes, 2.6 Shots each, longest 5 — stays with a Scene",
            "now recurring in the record, seen clearly in at least three separate Shots: "
            "backlight; recurrence does not prove deliberate control",
            "the photographer has not marked enough Keepers to say what they value — "
            "do not speak about taste",
        ],
    },
    {
        "id": "change_is_not_causation",
        "taste": True,
        "previous": "You often centred one subject against warm light.",
        "evidence": [
            "27 Shots read in total.",
            "orientation widened since the last update, first time shooting portrait",
            "was offered negative space to try, after centred 12 of 18 readable; in their "
            "Shots since: placement widened from centred 67% to centred 44%",
            "6 Shots marked as Keepers by the photographer themselves.",
            "cannot see: reliable Camera height",
        ],
    },
)


async def run() -> list[dict[str, object]]:
    results = []
    for case in CASES:
        body = await journey.write(
            case["evidence"],
            case["previous"],
            case["taste"],
        )
        lowered = body.lower()
        failures = []
        if not body:
            failures.append("writer returned no usable paragraph")
        if len(body.split()) > 90:
            failures.append("paragraph exceeded 90 words")
        failures.extend(
            f"unsupported phrase: {phrase}" for phrase in FORBIDDEN if phrase in lowered
        )
        if not case["taste"] and any(word in lowered for word in ("value", "prefer", "taste")):
            failures.append("unknown taste was presented as Photographer preference")
        results.append({"id": case["id"], "body": body, "failures": failures})
    return results


def main() -> int:
    results = asyncio.run(run())
    report = {
        "model": settings.model_flash,
        "provider": "vertex" if settings.use_vertex_ai else "ai_studio",
        "prompt_version": prompts.version("journey"),
        "cases": results,
        "passed": sum(not result["failures"] for result in results),
        "failed": sum(bool(result["failures"]) for result in results),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
