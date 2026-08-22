"""Shared Pillow helpers: loading, scaling, fonts, and byte conversion."""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

#: Long-edge cap before anything is sent to a model. Keeps token cost predictable
#: without starving the Scanner of detail; the zoom pass supplies real resolution.
MAX_MODEL_EDGE = 1536


def load(path: str | Path) -> Image.Image:
    """Open an image as RGB, honouring EXIF rotation."""
    from PIL import ImageOps

    image = Image.open(path)
    image = ImageOps.exif_transpose(image)
    return image.convert("RGB")


def to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def from_bytes(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def fit_for_model(image: Image.Image, max_edge: int = MAX_MODEL_EDGE) -> Image.Image:
    """Downscale so the long edge is at most ``max_edge``. Never upscales."""
    longest = max(image.size)
    if longest <= max_edge:
        return image
    scale = max_edge / longest
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.LANCZOS)


def font_for(size: int) -> ImageFont.FreeTypeFont:
    """A truetype font at a usable size, falling back to Pillow's bitmap default."""
    for name in ("arial.ttf", "DejaVuSans.ttf", "Helvetica.ttc"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def draw_outlined_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int] = (255, 255, 255),
    outline: tuple[int, int, int] = (0, 0, 0),
    stroke: int = 2,
    anchor: str | None = None,
) -> None:
    """Text that stays legible on any background — required for grid labels."""
    draw.text(
        xy, text, font=font, fill=fill, stroke_width=stroke, stroke_fill=outline, anchor=anchor
    )
