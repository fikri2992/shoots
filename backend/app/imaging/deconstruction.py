"""Deterministic portrait carousel rendering for Deconstruction pages."""

from PIL import Image, ImageDraw, ImageOps

from app.domain.entities import DeconstructionPage
from app.imaging.canvas import font_for

WIDTH = 1080
HEIGHT = 1350
IMAGE_HEIGHT = 930
INK = (13, 13, 14)
INK_SOFT = (28, 27, 25)
WARM_WHITE = (245, 239, 229)
MUTED = (166, 160, 151)
AMBER = (224, 166, 73)


def render(
    page: DeconstructionPage,
    images: list[Image.Image],
    index: int,
    total: int,
) -> Image.Image:
    out = Image.new("RGB", (WIDTH, HEIGHT), INK)
    _draw_images(out, images)
    draw = ImageDraw.Draw(out)
    pad = 56
    title_font = font_for(34)
    claim_font = font_for(44)
    meta_font = font_for(24)
    draw.text((pad, 978), page.title.upper(), font=title_font, fill=AMBER)
    y = 1035
    for line in _wrap(draw, page.claim, claim_font, WIDTH - 2 * pad)[:4]:
        draw.text((pad, y), line, font=claim_font, fill=WARM_WHITE)
        y += 56
    draw.text((pad, 1300), "Deconstructed with Shoots", font=meta_font, fill=MUTED)
    draw.text((WIDTH - pad, 1300), f"{index}/{total}", font=meta_font, fill=MUTED, anchor="ra")
    return out


def _draw_images(out: Image.Image, images: list[Image.Image]) -> None:
    usable = [image.convert("RGB") for image in images[:4]]
    if not usable:
        ImageDraw.Draw(out).rectangle((0, 0, WIDTH, IMAGE_HEIGHT), fill=INK_SOFT)
        return
    if len(usable) == 1:
        out.paste(ImageOps.fit(usable[0], (WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS), (0, 0))
        return
    gap = 8
    cols = 2
    rows = 1 if len(usable) == 2 else 2
    tile_w = (WIDTH - gap) // cols
    tile_h = (IMAGE_HEIGHT - gap * (rows - 1)) // rows
    for position, image in enumerate(usable):
        col = position % cols
        row = position // cols
        tile = ImageOps.fit(image, (tile_w, tile_h), Image.Resampling.LANCZOS)
        out.paste(tile, (col * (tile_w + gap), row * (tile_h + gap)))


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if not line or draw.textlength(candidate, font=font) <= width:
            line = candidate
            continue
        lines.append(line)
        line = word
    if line:
        lines.append(line)
    return lines
