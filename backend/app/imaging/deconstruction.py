"""Deterministic portrait carousel rendering for Deconstruction pages."""

from PIL import Image, ImageDraw, ImageOps

from app.domain.entities import DeconstructionPage, DeconstructionPageKind
from app.imaging.canvas import font_for

WIDTH = 1080
HEIGHT = 1350
IMAGE_HEIGHT = 840
INK = (13, 13, 14)
INK_SOFT = (28, 27, 25)
WARM_WHITE = (245, 239, 229)
MUTED = (166, 160, 151)
AMBER = (224, 166, 73)
RENDER_VERSION = "deconstruction-story-render-2"


def render(
    page: DeconstructionPage,
    images: list[Image.Image],
    index: int,
    total: int,
) -> Image.Image:
    if page.kind is DeconstructionPageKind.COVER and images:
        return _render_cover(page, images[0], index, total)

    out = Image.new("RGB", (WIDTH, HEIGHT), INK)
    _draw_images(out, images)
    draw = ImageDraw.Draw(out)
    pad = 56
    title_font = font_for(32)
    claim_font = font_for(48)
    meta_font = font_for(24)
    draw.text((pad, 895), page.title, font=title_font, fill=AMBER)
    draw.text((WIDTH - pad, 895), f"{index:02d}", font=title_font, fill=MUTED, anchor="ra")
    y = 958
    for line in _wrap(draw, page.claim, claim_font, WIDTH - 2 * pad)[:4]:
        draw.text((pad, y), line, font=claim_font, fill=WARM_WHITE)
        y += 60
    draw.text((pad, 1300), "A Shoots story", font=meta_font, fill=MUTED)
    draw.text((WIDTH - pad, 1300), f"{index} of {total}", font=meta_font, fill=MUTED, anchor="ra")
    return out


def _render_cover(
    page: DeconstructionPage,
    image: Image.Image,
    index: int,
    total: int,
) -> Image.Image:
    out = ImageOps.fit(image.convert("RGB"), (WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    shade = ImageDraw.Draw(overlay)
    for y in range(HEIGHT):
        lower = max(0.0, (y - 500) / (HEIGHT - 500))
        alpha = round(24 + 205 * lower * lower)
        shade.line((0, y, WIDTH, y), fill=(8, 8, 10, min(alpha, 225)))
    out = Image.alpha_composite(out.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(out)
    pad = 58
    title_font = font_for(32)
    claim_font = font_for(60)
    meta_font = font_for(24)
    draw.text((pad, 955), page.title, font=title_font, fill=AMBER)
    y = 1018
    lines = _wrap(draw, page.claim, claim_font, WIDTH - 2 * pad)
    line_step = 72
    if len(lines) > 3:
        claim_font = font_for(48)
        lines = _wrap(draw, page.claim, claim_font, WIDTH - 2 * pad)
        line_step = 58
    for line in lines[:4]:
        draw.text((pad, y), line, font=claim_font, fill=WARM_WHITE)
        y += line_step
    draw.text((pad, 1300), "A Shoots story", font=meta_font, fill=WARM_WHITE)
    draw.text(
        (WIDTH - pad, 1300),
        f"{index} of {total}",
        font=meta_font,
        fill=WARM_WHITE,
        anchor="ra",
    )
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
