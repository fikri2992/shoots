"""Analyst stage: ``media.ingested`` → Analysis → ``media.analyzed``.

Idempotent on shot id: a shot that is already ANALYZED is skipped, and a
redelivery while a previous attempt is mid-flight will produce the same
document twice rather than two different ones (put is a full overwrite).
"""

import logging

from app.agents import analyst as agent
from app.domain.entities import ShotStatus, now
from app.imaging import canvas
from app.imaging.overlay import render_overlay
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.infra.storage import ANNOTATED, GRIDDED, ORIGINAL, SHEET, blob_path
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "analyst"


async def analyse(ctx: Context, message: dict) -> None:
    shot = await repo.get_shot(ctx.store, message["shot_id"])
    if shot.status is ShotStatus.ANALYZED:
        logger.info("analyst: %s already analysed, skipping", shot.id)
        return
    if shot.status is not ShotStatus.INGESTED or not shot.grid:
        logger.warning("analyst: %s is %s, nothing to analyse", shot.id, shot.status)
        return

    gridded = await ctx.blobs.read(shot.blobs[GRIDDED])
    clean_key = SHEET if SHEET in shot.blobs else ORIGINAL
    clean = canvas.fit_for_model(canvas.load_bytes(await ctx.blobs.read(shot.blobs[clean_key])))
    result = await agent.analyse(shot, gridded, canvas.to_jpeg_bytes(clean))
    analysis = agent.validate(shot, result)
    await repo.put_analysis(ctx.store, analysis)

    # A rendered copy of the composition read, on the frame the model saw
    # (the sheet for video, the original for photos). The dashboard draws its
    # own SVG; this one is for the activity feed, emails and the demo.
    base_key = SHEET if SHEET in shot.blobs else ORIGINAL
    base = canvas.load_bytes(await ctx.blobs.read(shot.blobs[base_key]))
    annotated = render_overlay(base, shot.grid, analysis.composition)
    shot.blobs[ANNOTATED] = await ctx.blobs.write(
        blob_path(shot.user_id, shot.id, ANNOTATED, "jpg"),
        canvas.to_jpeg_bytes(annotated),
        "image/jpeg",
    )

    shot.status = ShotStatus.ANALYZED
    shot.analyzed_at = now()
    await repo.put_shot(ctx.store, shot)
    await repo.record(
        ctx.store,
        shot.user_id,
        AGENT,
        "analyzed",
        {
            "score": analysis.score,
            "techniques": [
                {
                    "id": t.technique_id,
                    "confidence": round(t.confidence, 2),
                    "agreement": t.agreement,
                    "lenses": t.lenses,
                }
                for t in analysis.techniques
            ],
            "elements": analysis.elements,
            "panel": analysis.panel,
            "moves": len(analysis.composition.moves),
        },
        shot_id=shot.id,
    )
    await ctx.bus.publish(TOPICS["media.analyzed"], {"shot_id": shot.id})
