"""Attach current Visual Evidence Artifacts without rerunning Gemini.

Use after a renderer upgrade for existing still Analyses. The authoritative
Technique Evidence is unchanged; only code-created presentation artifacts are
added or replaced idempotently.
"""

from __future__ import annotations

import argparse
import asyncio

from app.api.deps import get_context
from app.domain import technique_map
from app.domain.entities import ShotKind
from app.imaging import canvas, visual_evidence
from app.infra import repository as repo
from app.infra.storage import ORIGINAL, SHEET
from app.services import analyst
from app.services.context import Context


async def run(
    user_id: str = "",
    force: bool = False,
    context: Context | None = None,
) -> dict[str, int]:
    ctx = context or get_context()
    users = await repo.list_users(ctx.store)
    if user_id:
        users = [user for user in users if user.id == user_id]
    result = {"users": len(users), "shots": 0, "updated": 0, "skipped": 0, "failed": 0}
    for user in users:
        for shot in await repo.list_shots(ctx.store, user.id):
            if shot.kind is not ShotKind.PHOTO:
                continue
            analysis = await repo.find_analysis(ctx.store, shot.id)
            if analysis is None or not analysis.techniques:
                continue
            result["shots"] += 1
            visible = [item for item in analysis.techniques if technique_map.corroborated(item)]
            current = all(
                item.visual_artifact is not None
                and item.visual_artifact.renderer_version == visual_evidence.RENDERER_VERSION
                for item in visible
            )
            if current and not force:
                result["skipped"] += 1
                continue
            base_key = SHEET if SHEET in shot.blobs else ORIGINAL
            path = shot.blobs.get(base_key, "")
            if not path:
                result["failed"] += 1
                continue
            try:
                source = await ctx.blobs.read(path)
                image = canvas.load_bytes(source)
                await analyst.render_visual_evidence(ctx, shot, analysis, image, source)
                await repo.put_analysis(ctx.store, analysis)
                await repo.record(
                    ctx.store,
                    shot.user_id,
                    "analyst",
                    "visual_evidence_backfilled",
                    {
                        "renderer_version": visual_evidence.RENDERER_VERSION,
                        "techniques": len(analysis.techniques),
                    },
                    shot_id=shot.id,
                )
                result["updated"] += 1
            except Exception:  # noqa: BLE001 — continue across the archive
                result["failed"] += 1
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="", help="Photographer id; default is every user")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(run(args.user, args.force))
    print(" ".join(f"{key}={value}" for key, value in result.items()))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
