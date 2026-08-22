"""Real ffmpeg: a generated clip plus a generated tone come out as one playable mp4."""

import asyncio
import math
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

import pytest

from app.imaging import mux, video


def sine_wav(seconds: float, rate: int = 48000) -> bytes:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder, "tone.wav")
        with wave.open(str(path), "wb") as out:
            out.setnchannels(2)
            out.setsampwidth(2)
            out.setframerate(rate)
            frames = bytearray()
            for i in range(int(seconds * rate)):
                sample = int(12000 * math.sin(2 * math.pi * 440 * i / rate))
                frames += struct.pack("<hh", sample, sample)
            out.writeframes(bytes(frames))
        return path.read_bytes()


def silent_clip(seconds: float) -> bytes:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder, "clip.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=gray:s=180x320:d={seconds}:r=24",
                "-pix_fmt",
                "yuv420p",
                str(path),
            ],
            check=True,
        )
        return path.read_bytes()


def test_track_is_trimmed_to_the_clip():
    clip = silent_clip(2.0)
    scored = asyncio.run(mux.score(clip, sine_wav(10.0), duration=2.0))
    info = asyncio.run(video.probe(scored))
    assert 1.9 <= info.duration <= 2.2
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder, "scored.mp4")
        path.write_bytes(scored)
        streams = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    assert sorted(streams) == ["audio", "video"]


def test_bad_duration_rejected():
    with pytest.raises(ValueError):
        asyncio.run(mux.score(b"", b"", duration=0))
