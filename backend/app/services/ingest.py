"""Ingest: a Drive file becomes a Shot with hard evidence and model-ready images.

Two entry points:

* ``sync`` lists the user's folder and creates a NEW shot per unseen file,
  publishing ``media.new`` for each. Safe to call any number of times: the
  shot id is derived from the Drive file id, so a known file is skipped.
* ``ingest`` is the ``media.new`` handler. It atomically claims the Shot,
  downloads the file, reads EXIF or ffprobe, draws the grid, tiles video
  frames, writes blobs and publishes ``media.ingested``. Concurrent delivery
  has one owner; a stale claim can be taken over.
"""

import logging
from datetime import UTC, timedelta
from json import JSONDecodeError

from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.domain import motion as motion_rules
from app.domain import tone as tone_rules
from app.domain.entities import (
    GridSpec,
    Shot,
    ShotKind,
    ShotSource,
    ShotStatus,
    User,
    VideoMeta,
    now,
)
from app.domain.grid import Grid
from app.imaging import canvas, motion, video
from app.imaging.contact_sheet import tile_sheet
from app.imaging.exif import read_exif
from app.imaging.grid_overlay import apply_grid
from app.imaging.tone import measure as measure_tone
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.infra.drive import DriveFile
from app.infra.storage import GRIDDED, ORIGINAL, SHEET, THUMB, blob_path, extension_for
from app.services import runs
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "ingest"
_LEASE_SECONDS = 600.0
THUMB_EDGE = 512
SHEET_TILE_WIDTH = 480


class PermanentMediaError(ValueError):
    """The downloaded bytes are proven unreadable or unsupported."""


# --- sync -------------------------------------------------------------------


async def sync(ctx: Context, user: User) -> list[Shot]:
    """Create NEW shots for files in the folder we have not seen. Returns them."""
    if not user.drive_folder_id:
        return []
    files = await ctx.drive.list_media(user.drive_folder_id)
    created: list[Shot] = []
    for file in files:
        inspiration_id = repo.source_inspiration_id_for(
            user.id,
            ShotSource.DRIVE_PICKER.value,
            file.id,
        )
        inspiration = await repo.find_inspiration(ctx.store, inspiration_id)
        if inspiration is not None and not inspiration.superseded_at:
            continue
        shot_id = repo.shot_id_for(user.id, file.id)
        if await repo.find_shot(ctx.store, shot_id):
            continue
        shot = new_shot(shot_id, user.id, file)
        await repo.put_shot(ctx.store, shot)
        await runs.ensure(ctx, shot)
        await repo.record(
            ctx.store, user.id, AGENT, "queued", {"filename": file.name}, shot_id=shot.id
        )
        await ctx.bus.publish(TOPICS["media.new"], {"shot_id": shot.id})
        created.append(shot)
    return created


def new_shot(shot_id: str, user_id: str, file: DriveFile, experiment_id: str = "") -> Shot:
    kind = ShotKind.VIDEO if file.mime_type.startswith("video/") else ShotKind.PHOTO
    return Shot(
        id=shot_id,
        user_id=user_id,
        kind=kind,
        source=ShotSource.DRIVE,
        source_id=file.id,
        drive_file_id=file.id,
        filename=file.name,
        mime_type=file.mime_type,
        experiment_id=experiment_id,
    )


# --- ingest ---------------------------------------------------------------


async def ingest(ctx: Context, message: dict) -> None:
    claimed_at = now()
    shot, claimed = await repo.claim_shot_for_ingest(
        ctx.store,
        message["shot_id"],
        claimed_at,
        claimed_at - timedelta(seconds=_LEASE_SECONDS),
    )
    if not claimed and shot.status is ShotStatus.INGESTED:
        # The status commit may have succeeded while the downstream publish
        # was lost. Replaying is safe: every later stage is idempotent.
        await ctx.bus.publish(TOPICS["media.ingested"], {"shot_id": shot.id})
        return
    if not claimed:
        logger.info("ingest: %s already %s, skipping", shot.id, shot.status)
        return

    try:
        if ORIGINAL in shot.blobs:
            data = await ctx.blobs.read(shot.blobs[ORIGINAL])
        elif shot.drive_file_id:
            data = await ctx.drive.download(shot.drive_file_id)
        else:
            raise FileNotFoundError(f"no original bytes for {shot.id}")
        if shot.kind is ShotKind.VIDEO:
            shot = await _ingest_video(ctx, shot, data)
        else:
            shot = await _ingest_photo(ctx, shot, data)

        detail = {
            "kind": shot.kind.value,
            "grid": f"{shot.grid.cols}x{shot.grid.rows}" if shot.grid else "",
            "exif": shot.exif.model_dump(mode="json", exclude_none=True),
            "video": shot.video.model_dump(mode="json", exclude_none=True) if shot.video else None,
            "tone": tone_rules.describe(shot.tone, shot.exif),
            "motion": motion_rules.describe(shot.motion),
        }
        await _remember_location(ctx, shot)
        await repo.record(
            ctx.store,
            shot.user_id,
            AGENT,
            "ingested",
            detail,
            shot_id=shot.id,
        )
        shot.status = ShotStatus.INGESTED
        shot.ingesting_at = None
        shot.error = ""
        await repo.put_shot(ctx.store, shot)
    except PermanentMediaError as error:
        shot.status = ShotStatus.FAILED
        shot.ingesting_at = None
        shot.error = f"{type(error).__name__}: {error}"[:500]
        await repo.put_shot(ctx.store, shot)
        await repo.record(
            ctx.store, shot.user_id, AGENT, "failed", {"error": shot.error}, shot_id=shot.id
        )
        return
    except Exception as error:
        # Delivery, storage, and missing-dependency failures are retryable. The
        # idempotency key remains NEW so a redelivery can finish the same Shot.
        shot.status = ShotStatus.NEW
        shot.ingesting_at = None
        shot.error = f"{type(error).__name__}: {error}"[:500]
        await repo.put_shot(ctx.store, shot)
        await repo.record(
            ctx.store, shot.user_id, AGENT, "retrying", {"error": shot.error}, shot_id=shot.id
        )
        raise

    await ctx.bus.publish(TOPICS["media.ingested"], {"shot_id": shot.id})


async def resume(ctx: Context, shot: Shot) -> None:
    """Republish the stage implied by one already accepted Shot.

    Android may retry an ambiguous ingress response, and older accepted Shots
    may predate durable Run accounting. The Shot status is the durable handoff
    point, so recovery uses it instead of guessing from elapsed time.
    """
    if shot.status in {ShotStatus.NEW, ShotStatus.INGESTING}:
        await ctx.bus.publish(TOPICS["media.new"], {"shot_id": shot.id})
    elif shot.status in {ShotStatus.INGESTED, ShotStatus.ANALYSING}:
        await ctx.bus.publish(TOPICS["media.ingested"], {"shot_id": shot.id})


async def _ingest_photo(ctx: Context, shot: Shot, data: bytes) -> Shot:
    shot.exif = read_exif(data)
    shot.captured_at = shot.exif.captured_at
    try:
        image = canvas.load_bytes(data)
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise PermanentMediaError("image bytes cannot be decoded") from error
    # Beside the EXIF, because the camera records that it chose a white balance
    # and never which one: colour is only evidence once it is measured.
    shot.tone = measure_tone(image)

    extension = extension_for(shot.mime_type)
    shot.blobs[ORIGINAL] = await ctx.blobs.write(
        blob_path(shot.user_id, shot.id, ORIGINAL, extension), data, shot.mime_type
    )
    shot.grid = await _write_gridded(ctx, shot, image)
    await _write_thumb(ctx, shot, image)
    return shot


async def _ingest_video(ctx: Context, shot: Shot, data: bytes) -> Shot:
    try:
        info = await video.probe(data)
        cuts = await video.scene_times(data)
        times = sample_times(
            info.duration, cuts, settings.video_min_frames, settings.video_max_frames
        )
        frames = [canvas.from_bytes(await video.frame_at(data, t)) for t in times]
        loudness = await video.measure_loudness(data)
        tone = measure_tone(frames[0])
        measured_motion = await motion.measure(data)
    except FileNotFoundError:
        # ffmpeg/ffprobe missing is an environment failure, not bad media.
        raise
    except (
        video.FfmpegError,
        JSONDecodeError,
        KeyError,
        IndexError,
        UnidentifiedImageError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        raise PermanentMediaError("video bytes cannot be decoded") from error

    shot.video = VideoMeta(
        duration_s=info.duration,
        fps=info.fps,
        width=info.width,
        height=info.height,
        codec=info.codec,
        lufs=loudness.lufs if loudness else None,
    )
    # Tone off a real frame, never off the contact sheet: the sheet's padding
    # and caption band are black and white in fixed proportions, so measuring
    # it would report the sheet's palette rather than the photographer's.
    shot.tone = tone
    # And how the camera moved, which the sheet genuinely cannot show: its
    # tiles are scene cuts seconds apart, and a pan, a tracking shot and a cut
    # all look the same across that gap (domain/motion.py).
    shot.motion = measured_motion

    extension = extension_for(shot.mime_type)
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
    """The newest Shot with GPS tells Scout where the photographer shoots, so an
    experiment can be timed to the light there (domain/timing.py)."""
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
