"""Video → ``entities.Motion``. How the camera moved, measured between frames.

The contact sheet cannot answer this. Its frames are scene cuts spread over
the whole clip, so two neighbouring tiles may be four seconds apart; a pan, a
tracking shot and a cut all look identical across that gap. Twelve video
techniques were being guessed from it and were landing at 0.11 sightings per
shot, against 1.94 for composition — not because the lenses were careless but
because the evidence was not in front of them.

Consecutive frames do hold it. This pulls a dense low-resolution strip with
one ffmpeg call and phase-correlates each neighbouring pair: the peak of the
inverse transform of the normalised cross-power spectrum is the global shift
between two frames. It is the standard registration method, it is exact for a
pure translation, and it degrades to noise rather than to a confident wrong
answer when the frame content changes instead of moving — which is what a cut
is, and why cuts show up as reversals rather than as drift.

64x36 is deliberate. Camera moves worth naming are a large fraction of the
frame, translation is measured in whole pixels here, and one pixel at this
width is 1.6% of the frame — finer than any move a photographer would call
static. Downsampling this far also washes out subject motion, leaving the
camera's own movement, which is the thing being measured.

Rotation and zoom are not measured, so orbit, push-in and rack focus get no
facts from here. That is the honest limit of translation-only registration
and the reason ``domain/motion.py`` names only what it can prove.
"""

import asyncio
import logging
from dataclasses import dataclass

import numpy as np

from app.domain.entities import Motion
from app.imaging.video import FfmpegError, run, source

logger = logging.getLogger(__name__)

#: The strip the measurement runs on.
SAMPLE_FPS = 4.0
SAMPLE_WIDTH = 64
SAMPLE_HEIGHT = 36
#: A clip longer than this is measured over its first ``MAX_SAMPLES`` frames.
#: At 4 fps that is two minutes, past which a single "camera move" is a
#: sequence of them and no one number describes it.
MAX_SAMPLES = 480

#: Below this a step is the compression noise floor, not a move: measured over
#: the corpus, a locked-off clip on a table averages 0.1% per step and a slow
#: deliberate pan averages 1.8%, so 0.5% separates them with room either side.
STILL_STEP = 0.005


@dataclass(frozen=True)
class Strip:
    """Grayscale frames as ``(n, height, width)``, and the rate they were cut at."""

    frames: np.ndarray
    fps: float


async def sample_strip(data: bytes, fps: float = SAMPLE_FPS) -> Strip | None:
    """One ffmpeg call: decode to a tiny grayscale raw strip. None if too short."""
    try:
        with source(data) as path:
            stdout, _ = await run(
                "ffmpeg",
                "-v",
                "error",
                "-i",
                path,
                "-vf",
                f"fps={fps:g},scale={SAMPLE_WIDTH}:{SAMPLE_HEIGHT}",
                "-frames:v",
                str(MAX_SAMPLES),
                "-f",
                "rawvideo",
                "-pix_fmt",
                "gray",
                "pipe:1",
            )
    except FfmpegError as error:
        logger.warning("motion: ffmpeg would not decode the strip: %s", error)
        return None

    stride = SAMPLE_WIDTH * SAMPLE_HEIGHT
    count = len(stdout) // stride
    if count < 2:
        return None
    frames = np.frombuffer(stdout[: count * stride], dtype=np.uint8)
    return Strip(
        frames=frames.reshape(count, SAMPLE_HEIGHT, SAMPLE_WIDTH).astype(np.float32), fps=fps
    )


def shift_between(first: np.ndarray, second: np.ndarray) -> tuple[int, int]:
    """Whole-pixel translation from ``first`` to ``second``, by phase correlation."""
    height, width = first.shape
    spectrum = np.fft.rfft2(first) * np.conj(np.fft.rfft2(second))
    # Normalising to unit magnitude is what makes this phase correlation rather
    # than plain cross-correlation: it discards how bright the frames are and
    # keeps only how they line up, so a shot that darkens does not read as a move.
    correlation = np.fft.irfft2(spectrum / (np.abs(spectrum) + 1e-9), s=first.shape)
    dy, dx = np.unravel_index(int(np.argmax(correlation)), correlation.shape)
    # The transform wraps: the top-left quadrant is a positive shift and the
    # rest is the negative one folded around.
    return (int(dx) - width if dx > width // 2 else int(dx)), (
        int(dy) - height if dy > height // 2 else int(dy)
    )


def from_strip(strip: Strip) -> Motion:
    """Pure, given the frames: everything ``domain/motion.py`` reasons about."""
    steps = [
        shift_between(strip.frames[i], strip.frames[i + 1]) for i in range(len(strip.frames) - 1)
    ]
    dx = np.array([s[0] for s in steps], dtype=np.float64) / SAMPLE_WIDTH
    dy = np.array([s[1] for s in steps], dtype=np.float64) / SAMPLE_HEIGHT
    magnitude = np.hypot(dx, dy)

    moving = np.sign(dx[np.abs(dx) > STILL_STEP])
    reversals = int(np.count_nonzero(np.diff(moving))) if moving.size > 1 else 0

    return Motion(
        frames=len(strip.frames),
        fps=strip.fps,
        drift_x=round(float(dx.sum()), 3),
        drift_y=round(float(dy.sum()), 3),
        step=round(float(magnitude.mean()), 4),
        step_max=round(float(magnitude.max()), 4),
        reversals=reversals,
        still_share=round(float(np.mean(magnitude <= STILL_STEP)), 3),
    )


async def measure(data: bytes) -> Motion | None:
    """Measure one clip. None when ffmpeg cannot give us two frames to compare."""
    strip = await sample_strip(data)
    if strip is None:
        return None
    return await asyncio.to_thread(from_strip, strip)
