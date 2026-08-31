"""Real Scout acceptance checks for equipment-aware visual-goal instructions.

Controlled text inputs, not a visual-quality benchmark or production workflow.
No Photographer records are created or changed.
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

from app.agents import prompts, scout
from app.config import settings
from app.domain import experiment_criteria, taxonomy
from app.domain.entities import CameraCapabilities, CameraCapability, Constraints, ExperimentType


async def check(label: str, apertures: list[float] | None) -> dict:
    constraints = Constraints(
        camera_reports=[
            CameraCapabilities(
                manufacturer="Acceptance fixture",
                model=label,
                cameras=[CameraCapability(camera_id="0", facing="back", apertures=apertures)],
            )
        ]
    )
    at = time.monotonic()
    try:
        result = await scout.write(
            taxonomy.BY_ID["deep_dof"],
            "A marked Keeper shows nearby and distant detail.",
            [],
            scout.Research(
                notes=(
                    "Controlled regression input: a conventional interchangeable-lens guide "
                    "recommends f/8 and aperture priority for landscapes. This generic recipe "
                    "does not establish the available controls of the Photographer's Camera."
                )
            ),
            {},
            constraints,
            ExperimentType.REPRODUCE,
        )
        criteria = scout.criteria_for(taxonomy.BY_ID["deep_dof"], result.criteria_text)
        experiment_criteria.validate_visual_advice("deep_dof", result.model_dump_json())
        return {
            "case": label,
            "seconds": round(time.monotonic() - at, 2),
            "accepted": True,
            "output": result.model_dump(),
            "criteria": criteria.model_dump(),
        }
    except Exception as error:
        return {
            "case": label,
            "seconds": round(time.monotonic() - at, 2),
            "accepted": False,
            "error_type": type(error).__name__,
            "error": str(error)[:300],
        }


async def main(output: Path) -> None:
    results = await asyncio.gather(
        check("fixed aperture", [1.7]),
        check("adjustable aperture", [2.8, 4.0, 8.0]),
        check("unknown aperture", None),
    )
    report = {
        "scope": "Real Scout writing only; controlled inputs; no visual quality claim",
        "model": settings.model_flash,
        "prompt_version": prompts.version("scout"),
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(output),
                "accepted": sum(r["accepted"] for r in results),
                "cases": [{k: row[k] for k in ("case", "accepted", "seconds")} for row in results],
            }
        )
    )
    if not all(row["accepted"] for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args().output))
