"""Video ingestion mechanics (phase 13, decision 23): ffmpeg, nothing clever.

A video reviews as shots: scene-cut detection yields representative frames that
run the existing image pipeline, and loudness is measured once at ingest with
EBU R128 — arithmetic stated alongside any verdict, never a model's opinion of
a sound level.

Everything here shells out to ffmpeg/ffprobe and stays I/O-only; deciding what
the numbers mean happens in the domain layers that already exist.
"""

import asyncio
import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

#: Scene-change score above which a new shot begins. ffmpeg's usual default.
SCENE_THRESHOLD = 0.3

#: Hard cap on frames per video — the pipeline cost cap, not a quality knob.
MAX_FRAMES = 12


class FfmpegError(RuntimeError):
    pass


@dataclass
class VideoInfo:
    width: int
    height: int
    duration: float


@dataclass
class Loudness:
    """EBU R128 integrated loudness and true peak — the audio measured half."""

    lufs: float
    true_peak_db: float


async def _run(*args: str, payload: bytes | None = None) -> tuple[bytes, bytes]:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE if payload is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await process.communicate(payload)
    if process.returncode != 0:
        raise FfmpegError(f"{args[0]} failed: {err.decode(errors='replace')[-400:]}")
    return out, err


async def probe(data: bytes) -> VideoInfo:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as handle:
        handle.write(data)
        path = handle.name
    try:
        out, _ = await _run(
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-show_entries", "format=duration",
            "-of", "json", path,
        )
        document = json.loads(out)
        stream = document["streams"][0]
        return VideoInfo(
            width=int(stream["width"]),
            height=int(stream["height"]),
            duration=float(document["format"]["duration"]),
        )
    finally:
        Path(path).unlink(missing_ok=True)


async def scene_times(data: bytes, threshold: float = SCENE_THRESHOLD) -> list[float]:
    """Timestamps where shots begin: 0.0 plus every detected cut, capped."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as handle:
        handle.write(data)
        path = handle.name
    try:
        _, err = await _run(
            "ffmpeg", "-i", path,
            "-vf", f"select='gt(scene,{threshold})',showinfo",
            "-f", "null", "-",
        )
        cuts = [float(m) for m in re.findall(r"pts_time:([\d.]+)", err.decode(errors="replace"))]
        times = [0.0, *cuts]
        return times[:MAX_FRAMES]
    finally:
        Path(path).unlink(missing_ok=True)


async def frame_at(data: bytes, at: float) -> bytes:
    """One PNG frame at ``at`` seconds — what the image pipeline will judge."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as handle:
        handle.write(data)
        path = handle.name
    try:
        out, _ = await _run(
            "ffmpeg", "-ss", f"{at:.3f}", "-i", path,
            "-frames:v", "1", "-f", "image2", "-c:v", "png", "pipe:1",
        )
        if not out:
            raise FfmpegError(f"no frame at {at:.3f}s")
        return out
    finally:
        Path(path).unlink(missing_ok=True)


async def measure_loudness(data: bytes) -> Loudness | None:
    """Integrated LUFS + true peak, or None for a silent/audio-less file."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as handle:
        handle.write(data)
        path = handle.name
    try:
        try:
            _, err = await _run(
                "ffmpeg", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"
            )
        except FfmpegError:
            return None  # no audio stream
        text = err.decode(errors="replace")
        # ebur128 prints running values as it goes; only the final summary block
        # holds the integrated figure — so the LAST match is the measurement.
        integrated = re.findall(r"I:\s*(-?[\d.]+)\s*LUFS", text)
        peaks = re.findall(r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS", text)
        if not integrated:
            return None
        peak_value = peaks[-1] if peaks else "-inf"
        return Loudness(
            lufs=float(integrated[-1]),
            true_peak_db=float("-inf") if peak_value == "-inf" else float(peak_value),
        )
    finally:
        Path(path).unlink(missing_ok=True)
