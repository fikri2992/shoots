"""Analyst stage: ``media.ingested`` → Analysis → ``media.analyzed``.

Idempotent on shot id, and on cost. A shot that is already ANALYZED is
skipped, which has always been free. The expensive case was the other one:
this stage spends four to six model calls before it writes anything, so a
failure *after* ``agent.analyse()`` returned — the overlay render, a blob
write, the repository write — left the shot at INGESTED and the redelivery
paid for the whole panel again. With five delivery attempts that is twenty
lens calls and about four minutes for one shot.

So the shot is moved to ANALYSING before the first model call, and a
redelivery that finds it there returns. The claim is dated: an attempt that
died leaves the status behind with nothing coming to clear it, so a claim
older than ``_LEASE_SECONDS`` — the panel's own timeout plus the slack the
rest of the stage needs — is treated as dead and taken over.
"""

import logging
from datetime import timedelta

from app.agents import analyst as agent
from app.agents import crop as crop_loop
from app.agents import scrub as scrub_lens
from app.domain.entities import ShotKind, ShotStatus, now
from app.domain.grid import Grid
from app.imaging import canvas, video
from app.imaging.grid_overlay import apply_grid
from app.imaging.overlay import render_overlay
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.infra.storage import ANNOTATED, CROP, GRIDDED, ORIGINAL, SHEET, blob_path
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "analyst"

#: How long another worker's ANALYSING claim is believed. The panel's own
#: timeout plus room for the crop loop, the overlay and the writes after it.
_LEASE_SECONDS = 420.0


def _in_flight(shot) -> bool:
    """Is someone else still working on this, or did their attempt die?"""
    if shot.status is not ShotStatus.ANALYSING:
        return False
    claimed = shot.analysing_at
    return claimed is not None and (now() - claimed) < timedelta(seconds=_LEASE_SECONDS)


async def analyse(ctx: Context, message: dict) -> None:
    shot = await repo.get_shot(ctx.store, message["shot_id"])
    if shot.status is ShotStatus.ANALYZED:
        logger.info("analyst: %s already analysed, skipping", shot.id)
        return
    if _in_flight(shot):
        logger.info("analyst: %s is mid-panel elsewhere, skipping", shot.id)
        return
    if shot.status not in (ShotStatus.INGESTED, ShotStatus.ANALYSING) or not shot.grid:
        logger.warning("analyst: %s is %s, nothing to analyse", shot.id, shot.status)
        return

    # Claimed before any model call: everything below here costs money.
    shot.status = ShotStatus.ANALYSING
    shot.analysing_at = now()
    await repo.put_shot(ctx.store, shot)

    gridded = await ctx.blobs.read(shot.blobs[GRIDDED])
    clean_key = SHEET if SHEET in shot.blobs else ORIGINAL
    clean = canvas.fit_for_model(canvas.load_bytes(await ctx.blobs.read(shot.blobs[clean_key])))
    result = await agent.analyse(shot, gridded, canvas.to_jpeg_bytes(clean))
    if shot.kind is ShotKind.VIDEO:
        await _scrub(ctx, shot, result)
    analysis = agent.validate(shot, result)
    await _test_crop(ctx, shot, analysis, clean, gridded)
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
    shot.analysing_at = None
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
            "dissent": analysis.dissent,
            "crop": {
                "tested": analysis.composition.crop_tested,
                "kept": bool(analysis.composition.suggested_crop_cells),
                "before": analysis.composition.crop_before,
                "after": analysis.composition.crop_after,
                "rounds": analysis.composition.crop_rounds,
            },
            "moves": len(analysis.composition.moves),
        },
        shot_id=shot.id,
    )
    await ctx.bus.publish(TOPICS["media.analyzed"], {"shot_id": shot.id})


async def _test_crop(ctx: Context, shot, analysis, clean, gridded: bytes) -> None:
    """The Composer's crop must beat the original on the rendered image
    (agents/crop.py). A crop that did not is cleared, so the overlay never
    draws an untested suggestion; a failure here costs the crop, not the shot."""
    comp = analysis.composition
    if not comp.suggested_crop_cells or shot.kind.value == "video":
        comp.suggested_crop_cells = []
        return
    try:
        outcome = await crop_loop.refine(shot, clean, gridded, comp.suggested_crop_cells)
    except Exception:  # noqa: BLE001 — the reading stands without a tested crop
        logger.exception("crop loop failed for %s", shot.id)
        comp.suggested_crop_cells = []
        return
    comp.crop_tested = outcome.tested
    comp.crop_before = outcome.before
    comp.crop_after = outcome.after
    comp.crop_rounds = outcome.rounds
    comp.crop_reason = outcome.reason
    if outcome.kept and outcome.image:
        comp.suggested_crop_cells = outcome.cells
        shot.blobs[CROP] = await ctx.blobs.write(
            blob_path(shot.user_id, shot.id, CROP, "jpg"), outcome.image, "image/jpeg"
        )
    else:
        comp.suggested_crop_cells = []


async def _scrub(ctx: Context, shot, result) -> None:
    """Video: pull the two frames the Composer asked for (or two around the
    middle), grid them like the sheet, and let the scrub lens vote. A
    failure here costs one vote, not the reading."""
    import time

    composer = result.reads.get("composer")
    wanted = list(getattr(composer, "scrub_seconds", []) or [])[:2]
    duration = shot.video.duration_s if shot.video else 0.0
    times = sorted({min(max(0.0, float(t)), max(0.0, duration - 0.05)) for t in wanted})
    if len(times) < 2:
        times = scrub_lens.default_times(duration)
    try:
        data = await ctx.blobs.read(shot.blobs[ORIGINAL])
        started = time.monotonic()
        frames = []
        for t in times:
            frame = canvas.fit_for_model(canvas.load_bytes(await video.frame_at(data, t)))
            grid = Grid(
                cols=shot.grid.cols, rows=shot.grid.rows, width=frame.width, height=frame.height
            )
            frames.append((t, canvas.to_png_bytes(apply_grid(frame, grid))))
        result.reads["scrub"] = await scrub_lens.read(shot, frames)
        result.latency["scrub"] = time.monotonic() - started
    except Exception:  # noqa: BLE001 — the three-lens reading stands
        logger.exception("scrub lens failed for %s", shot.id)
