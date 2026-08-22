"""Put a music bed under a silent clip: ffmpeg, nothing clever.

The Director gets a video from Veo and a track from Lyria that do not know
about each other. This trims the track to the clip, fades it out, and
writes one mp4 the phone can play inline.
"""

import asyncio
import tempfile
from pathlib import Path

#: Seconds of fade at the end of the track so the loop point is not a cut.
FADE_SECONDS = 0.8


async def score(video: bytes, audio: bytes, duration: float, fade: float = FADE_SECONDS) -> bytes:
    """Return ``video`` with ``audio`` trimmed to ``duration`` seconds underneath.

    Video stream is copied untouched; audio is re-encoded to AAC so the
    result plays on every phone. ``audio`` may be any container ffmpeg reads.
    """
    if duration <= 0:
        raise ValueError("duration must be positive")
    fade = min(fade, duration / 2)
    with tempfile.TemporaryDirectory() as folder:
        video_path = Path(folder, "clip.mp4")
        audio_path = Path(folder, "track.bin")
        out_path = Path(folder, "scored.mp4")
        video_path.write_bytes(video)
        audio_path.write_bytes(audio)
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-filter_complex",
            f"[1:a]atrim=0:{duration:.3f},afade=t=out:st={duration - fade:.3f}:d={fade:.3f}[a]",
            "-map",
            "0:v:0",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, err = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"ffmpeg mux failed: {err.decode(errors='replace')[-400:]}")
        return out_path.read_bytes()
