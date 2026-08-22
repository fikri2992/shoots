"""A caption band under a frame, so the review reads anywhere the file goes:
Drive, Photos, a chat. Dark band, one bold title line, wrapped body lines."""

from PIL import Image, ImageDraw

from app.imaging.canvas import font_for

BAND = (18, 18, 20)
TITLE = (245, 245, 245)
BODY = (200, 200, 205)
MUTED = (120, 120, 128)


def add_caption(image: Image.Image, title: str, body: list[str], footer: str = "") -> Image.Image:
    """Returns a new image: ``image`` with a band below it holding the text."""
    width = image.width
    pad = max(16, width // 50)
    title_font = font_for(max(18, width // 40))
    body_font = font_for(max(14, width // 55))
    footer_font = font_for(max(12, width // 70))
    probe = ImageDraw.Draw(image)

    def wrap(text: str, font) -> list[str]:
        lines: list[str] = []
        for paragraph in text.split("\n"):
            words = paragraph.split()
            line = ""
            for word in words:
                trial = f"{line} {word}".strip()
                if probe.textlength(trial, font=font) <= width - 2 * pad:
                    line = trial
                else:
                    if line:
                        lines.append(line)
                    line = word
            lines.append(line)
        return lines

    title_lines = wrap(title, title_font)
    body_lines = [line for text in body for line in wrap(text, body_font)]
    footer_lines = wrap(footer, footer_font) if footer else []

    def height_of(lines: list[str], font) -> int:
        return sum(int(font.size * 1.35) for _ in lines)

    band_height = (
        pad
        + height_of(title_lines, title_font)
        + (pad // 2 if body_lines else 0)
        + height_of(body_lines, body_font)
        + (pad // 2 if footer_lines else 0)
        + height_of(footer_lines, footer_font)
        + pad
    )

    out = Image.new("RGB", (width, image.height + band_height), BAND)
    out.paste(image.convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(out)
    y = image.height + pad
    for line in title_lines:
        draw.text((pad, y), line, font=title_font, fill=TITLE)
        y += int(title_font.size * 1.35)
    if body_lines:
        y += pad // 2
    for line in body_lines:
        draw.text((pad, y), line, font=body_font, fill=BODY)
        y += int(body_font.size * 1.35)
    if footer_lines:
        y += pad // 2
    for line in footer_lines:
        draw.text((pad, y), line, font=footer_font, fill=MUTED)
        y += int(footer_font.size * 1.35)
    return out
