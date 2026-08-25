"""Real media for tests, generated on the fly: a JPEG with EXIF and, when
ffmpeg is present, a short two-shot video. No binary fixtures in git."""

import io
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def jpeg_with_exif(
    width: int = 1200,
    height: int = 800,
    exposure: tuple[int, int] = (1, 30),
    f_number: tuple[int, int] = (56, 10),
    iso: int = 200,
    focal: tuple[int, int] = (50, 1),
    focal35: int = 75,
    flash: int = 0,
    make: str = "TestCam",
    model: str = "T1",
    when: str = "2026:08:22 18:30:00",
    gps: tuple[float, float] | None = None,
) -> bytes:
    """A real JPEG whose EXIF block Pillow wrote, so the reader is tested
    against the same encoding cameras produce."""
    image = Image.new("RGB", (width, height), (40, 60, 90))
    draw = ImageDraw.Draw(image)
    draw.ellipse((width * 0.6, height * 0.3, width * 0.8, height * 0.6), fill=(230, 200, 80))
    draw.line((0, height * 0.7, width, height * 0.7), fill=(200, 200, 200), width=4)

    exif = Image.Exif()
    exif[0x010F] = make  # Make
    exif[0x0110] = model  # Model
    detail = exif.get_ifd(0x8769)  # Exif IFD
    detail[0x829A] = exposure  # ExposureTime
    detail[0x829D] = f_number  # FNumber
    detail[0x8827] = iso  # ISOSpeedRatings
    detail[0x9003] = when  # DateTimeOriginal
    detail[0x9209] = flash  # Flash
    detail[0x920A] = focal  # FocalLength
    detail[0xA405] = focal35  # FocalLengthIn35mmFilm
    detail[0xA434] = "Test 50mm f/1.8"  # LensModel
    if gps is not None:
        lat, lon = gps
        info = exif.get_ifd(0x8825)  # GPS IFD
        info[1] = "N" if lat >= 0 else "S"
        info[2] = _dms(abs(lat))
        info[3] = "E" if lon >= 0 else "W"
        info[4] = _dms(abs(lon))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90, exif=exif.tobytes())
    return buffer.getvalue()


def _dms(value: float) -> tuple[float, float, float]:
    degrees = int(value)
    minutes = int((value - degrees) * 60)
    seconds = round(((value - degrees) * 60 - minutes) * 60, 4)
    return (float(degrees), float(minutes), seconds)


def silent_clip(seconds: float) -> bytes:
    """A grey mp4 from lavfi: what a generated clip looks like to the code."""
    if not HAS_FFMPEG:
        raise RuntimeError("ffmpeg not installed")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "clip.mp4"
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
                str(out),
            ],
            check=True,
        )
        return out.read_bytes()


def _detailed_png(width: int, height: int) -> bytes:
    """A still with structure at every scale. Phase correlation needs texture:
    a flat grey frame has no features to line up and registering it would
    measure the compression noise."""
    image = Image.new("RGB", (width, height), (20, 20, 30))
    draw = ImageDraw.Draw(image)
    for i in range(0, width, 17):
        draw.line((i, 0, i + height // 3, height), fill=(90 + i % 120, 60, 200 - i % 150), width=3)
    for i in range(0, height, 23):
        draw.line((0, i, width, i + 9), fill=(230 - i % 100, 200 - i % 80, 40), width=2)
    for i in range(0, width, 61):
        draw.ellipse((i, height // 3, i + 28, height // 3 + 28), fill=(250, 240, 180))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _still_to_clip(png: bytes, seconds: float, video_filter: str, fps: int = 24) -> bytes:
    if not HAS_FFMPEG:
        raise RuntimeError("ffmpeg not installed")
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "frame.png"
        source.write_bytes(png)
        out = Path(tmp) / "clip.mp4"
        subprocess.run(
            [
                "ffmpeg", "-v", "error", "-y",
                "-loop", "1", "-framerate", str(fps), "-t", f"{seconds:g}",
                "-i", str(source),
                "-vf", video_filter,
                "-pix_fmt", "yuv420p", "-r", str(fps),
                str(out),
            ],
            check=True,
        )  # fmt: skip
        return out.read_bytes()


#: The window the synthesised camera looks through.
CLIP_WIDTH, CLIP_HEIGHT = 320, 240


def locked_clip(seconds: float = 3.0) -> bytes:
    """A detailed still, held. The framing never moves by a single pixel, so
    anything the measurement reports is its own noise floor."""
    png = _detailed_png(CLIP_WIDTH, CLIP_HEIGHT)
    return _still_to_clip(png, seconds, "null")


def panning_clip(seconds: float = 3.0, pixels_per_second: int = 100) -> bytes:
    """A pan of exactly known rate: a window slides right across a wide still.

    Ground truth for ``imaging/motion.py`` — the framing travels
    ``pixels_per_second x seconds`` pixels of a ``CLIP_WIDTH`` window, so the
    drift the measurement reports can be checked against arithmetic instead of
    against an opinion about what a pan looks like.
    """
    travel = int(pixels_per_second * seconds)
    png = _detailed_png(CLIP_WIDTH + travel, CLIP_HEIGHT)
    crop = f"crop={CLIP_WIDTH}:{CLIP_HEIGHT}:x='min(t*{pixels_per_second}\\,{travel})':y=0"
    return _still_to_clip(png, seconds, crop)


def two_shot_video(seconds: int = 2, fps: int = 30) -> bytes:
    """Red then blue solid frames with a hard cut: one scene change."""
    if not HAS_FFMPEG:
        raise RuntimeError("ffmpeg not installed")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "clip.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"color=c=red:s=320x240:d={seconds}:r={fps}",
                "-f",
                "lavfi",
                "-i",
                f"color=c=blue:s=320x240:d={seconds}:r={fps}",
                "-filter_complex",
                "[0:v][1:v]concat=n=2:v=1:a=0",
                "-pix_fmt",
                "yuv420p",
                str(out),
            ],
            check=True,
        )
        return out.read_bytes()
