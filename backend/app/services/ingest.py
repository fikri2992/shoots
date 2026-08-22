"""Ingest: a Drive file becomes a Shot with hard evidence and model-ready images.

Two entry points:

* ``sync`` lists the user's folder and creates a NEW shot per unseen file,
  publishing ``media.new`` for each. Safe to call any number of times: the
  shot id is derived from the Drive file id, so a known file is skipped.
* ``ingest`` is the ``media.new`` handler. It downloads the file, reads EXIF
  or ffprobe, draws the grid, tiles video frames, writes blobs and publishes
  ``media.ingested``. A redelivered message for a shot that is past NEW is a
  no-op (decision 7: idempotent on shot id).
"""

import logging
from datetime import UTC

from PIL import Image

from app.config import settings
from app.domain.entities import GridSpec, Shot, ShotKind, ShotStatus, User, VideoMeta, now
from app.domain.grid import Grid
from app.imaging import canvas, video
from app.imaging.contact_sheet import tile_sheet
from app.imaging.exif import read_exif
from app.imaging.grid_overlay import apply_grid
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.infra.drive import DriveFile
from app.infra.storage import GRIDDED, ORIGINAL, SHEET, THUMB, blob_path
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "ingest"
THUMB_EDGE = 512
SHEET_TILE_WIDTH = 480


# --- sync -------------------------------------------------------------------


async def sync(ctx: Context, user: User) -> list[Shot]:
    """Create NEW shots for files in the folder we have not seen. Returns them."""
    if not user.drive_folder_id:
        return []
    files = await ctx.drive.list_media(user.drive_folder_id)
    created: list[Shot] = []
    for file in files:
        shot_id = repo.shot_id_for(user.id, file.id)
        if await repo.find_shot(ctx.store, shot_id):
            continue
        shot = new_shot(shot_id, user.id, file)
        await repo.put_shot(ctx.store, shot)
        await repo.record(
            ctx.store, user.id, AGENT, "queued", {"filename": file.name}, shot_id=shot.id
        )
        await ctx.bus.publish(TOPICS["media.new"], {"shot_id": shot.id})
        created.append(shot)
    return created


def new_shot(shot_id: str, user_id: str, file: DriveFile, quest_id: str = "") -> Shot:
    kind = ShotKind.VIDEO if file.mime_type.startswith("video/") else ShotKind.PHOTO
    return Shot(
        id=shot_id,
        user_id=user_id,
        kind=kind,
        drive_file_id=file.id,
        filename=file.name,
        mime_type=file.mime_type,
        quest_id=quest_id,
    )


# --- ingest ---------------------------------------------------------------


async def ingest(ctx: Context, message: dict) -> None:
    shot = await repo.get_shot(ctx.store, message["shot_id"])
    if shot.status is not ShotStatus.NEW:
        logger.info("ingest: %s already %s, skipping", shot.id, shot.status)
        return

    try:
        data = await ctx.drive.download(shot.drive_file_id)
        if shot.kind is ShotKind.VIDEO:
            shot = await _ingest_video(ctx, shot, data)
        else:
            shot = await _ingest_photo(ctx, shot, data)
    except Exception as error:
        shot.status = ShotStatus.FAILED
        shot.error = f"{type(error).__name__}: {error}"[:500]
        await repo.put_shot(ctx.store, shot)
        await repo.record(
            ctx.store, shot.user_id, AGENT, "failed", {"error": shot.error}, shot_id=shot.id
        )
        raise

    shot.status = ShotStatus.INGESTED
    await repo.put_shot(ctx.store, shot)
    await _remember_location(ctx, shot)
    await repo.record(
        ctx.store,
        shot.user_id,
        AGENT,
        "ingested",
        {
            "kind": shot.kind.value,
            "grid": f"{shot.grid.cols}x{shot.grid.rows}" if shot.grid else "",
            "exif": shot.exif.model_dump(mode="json", exclude_none=True),
            "video": shot.video.model_dump(mode="json", exclude_none=True) if shot.video else None,
        },
        shot_id=shot.id,
    )
    await ctx.bus.publish(TOPICS["media.ingested"], {"shot_id": shot.id})


async def _ingest_photo(ctx: Context, shot: Shot, data: bytes) -> Shot:
    shot.exif = read_exif(data)
    shot.captured_at = shot.exif.captured_at
    image = canvas.load_bytes(data)

    extension = "jpg" if shot.mime_type == "image/jpeg" else "bin"
    shot.blobs[ORIGINAL] = await ctx.blobs.write(
        blob_path(shot.user_id, shot.id, ORIGINAL, extension), data, shot.mime_type
    )
    shot.grid = await _write_gridded(ctx, shot, image)
    await _write_thumb(ctx, shot, image)
    return shot


async def _ingest_video(ctx: Context, shot: Shot, data: bytes) -> Shot:
    info = await video.probe(data)
    cuts = await video.scene_times(data)
    times = sample_times(info.duration, cuts, settings.video_min_frames, settings.video_max_frames)
    frames = [canvas.from_bytes(await video.frame_at(data, t)) for t in times]
    loudness = await video.measure_loudness(data)

    shot.video = VideoMeta(
        duration_s=info.duration,
        fps=info.fps,
        width=info.width,
        height=info.height,
        codec=info.codec,
        lufs=loudness.lufs if loudness else None,
    )

    extension = "mp4" if shot.mime_type == "video/mp4" else "bin"
    shot.blobs[ORIGINAL] = await ctx.blobs.write(
        blob_path(shot.user_id, shot.id, ORIGINAL, extension), data, shot.mime_type
    )

    panels = [
        (f"{_mmss(t)}  frame {i + 1}/{len(times)}", f)
        for i, (t, f) in enumerate(zip(times, frames, strict=True))
    ]
    sheet = tile_sheet(panels, cols=settings.contact_sheet_cols, tile_width=SHEET_TILE_WIDTH)
    shot.blobs[SHEET] = await ctx.blobs.write(
        blob_path(shot.user_id, shot.id, SHEET, "png"), canvas.to_png_bytes(sheet)
    )
    shot.grid = await _write_gridded(ctx, shot, sheet)
    await _write_thumb(ctx, shot, frames[0])
    return shot


async def _write_gridded(ctx: Context, shot: Shot, image: Image.Image) -> GridSpec:
    """The exact pixels the Analyst will see, with the labelled grid on top."""
    fitted = canvas.fit_for_model(image, settings.analyst_max_edge)
    grid = Grid.for_image(fitted.width, fitted.height)
    gridded = apply_grid(fitted, grid)
    shot.blobs[GRIDDED] = await ctx.blobs.write(
        blob_path(shot.user_id, shot.id, GRIDDED, "png"), canvas.to_png_bytes(gridded)
    )
    return GridSpec(cols=grid.cols, rows=grid.rows, width=grid.width, height=grid.height)


async def _write_thumb(ctx: Context, shot: Shot, image: Image.Image) -> None:
    thumb = canvas.fit_for_model(image, THUMB_EDGE)
    shot.blobs[THUMB] = await ctx.blobs.write(
        blob_path(shot.user_id, shot.id, THUMB, "jpg"), canvas.to_jpeg_bytes(thumb), "image/jpeg"
    )


def sample_times(duration: float, cuts: list[float], minimum: int, maximum: int) -> list[float]:
    """Scene cuts plus an even spread so a continuous shot still gets frames.

    Pure: the evenly spaced candidates stop short of the end (a frame exactly
    at ``duration`` is often empty), cuts win ties, and the result is sorted,
    deduplicated to the nearest 0.25s and capped at ``maximum``.
    """
    if duration <= 0:
        return [0.0]
    minimum = max(1, minimum)
    spread = [duration * i / minimum for i in range(minimum)]
    merged: dict[float, float] = {}
    for t in [*cuts, *spread]:
        key = round(t * 4) / 4
        merged.setdefault(key, t)
    times = sorted(t for t in merged.values() if 0 <= t < duration) or [0.0]
    if len(times) > maximum:
        step = len(times) / maximum
        times = [times[int(i * step)] for i in range(maximum)]
    return times


def _mmss(seconds: float) -> str:
    whole = int(seconds)
    return f"{whole // 60}:{whole % 60:02d}"


async def _remember_location(ctx: Context, shot: Shot) -> None:
    """The newest frame with GPS tells the Scout where the user shoots, so a
    quest can be timed to the light there (domain/timing.py)."""
    if shot.exif.latitude is None or shot.exif.longitude is None:
        return
    user = await repo.find_user(ctx.store, shot.user_id)
    if user is None:
        return
    when = shot.captured_at or now()
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    if user.location_at and when <= user.location_at:
        return
    user.last_latitude = shot.exif.latitude
    user.last_longitude = shot.exif.longitude
    user.location_at = when
    await repo.put_user(ctx.store, user)
