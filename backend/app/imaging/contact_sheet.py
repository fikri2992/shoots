"""Contact sheets: several frames in one image, each captioned.

A video becomes a tiled sheet of scene-cut frames; the Analyst reads motion
and framing across the tiles. Captions carry the timestamp so the model can
say "the push-in happens between 0:02 and 0:05" in cell refs on the sheet.
"""

from PIL import Image, ImageDraw

from app.imaging.canvas import draw_outlined_text, font_for

BACKGROUND = (18, 18, 18)
CAPTION_BAR = 34
GUTTER = 12
PADDING = 12


def contact_sheet(panels: list[tuple[str, Image.Image]], panel_height: int = 720) -> Image.Image:
    """Lay captioned panels out in a single row, scaled to a common height."""
    if not panels:
        raise ValueError("a contact sheet needs at least one panel")

    scaled = [(caption, _scale_to_height(image, panel_height)) for caption, image in panels]

    width = sum(image.width for _, image in scaled) + GUTTER * (len(scaled) - 1) + PADDING * 2
    height = panel_height + CAPTION_BAR + PADDING * 2

    sheet = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    font = font_for(18)

    x = PADDING
    for caption, image in scaled:
        y = PADDING + CAPTION_BAR + (panel_height - image.height) // 2
        sheet.paste(image, (x, y))
        draw_outlined_text(draw, (x, PADDING + 6), caption, font=font, stroke=1)
        x += image.width + GUTTER

    return sheet


def tile_sheet(
    panels: list[tuple[str, Image.Image]], cols: int = 4, tile_width: int = 480
) -> Image.Image:
    """Grid of captioned tiles, reading order, all scaled to one width.

    Tile height is the tallest scaled frame so mixed orientations line up;
    shorter frames are centred in their tile.
    """
    if not panels:
        raise ValueError("a tile sheet needs at least one panel")
    if cols < 1:
        raise ValueError("cols must be positive")

    scaled = [(caption, _scale_to_width(image, tile_width)) for caption, image in panels]
    tile_height = max(image.height for _, image in scaled)
    rows = (len(scaled) + cols - 1) // cols
    used_cols = min(cols, len(scaled))

    width = PADDING * 2 + used_cols * tile_width + (used_cols - 1) * GUTTER
    height = PADDING * 2 + rows * (CAPTION_BAR + tile_height) + (rows - 1) * GUTTER

    sheet = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    font = font_for(16)

    for index, (caption, image) in enumerate(scaled):
        row, col = divmod(index, cols)
        x = PADDING + col * (tile_width + GUTTER)
        y = PADDING + row * (CAPTION_BAR + tile_height + GUTTER)
        sheet.paste(image, (x, y + CAPTION_BAR + (tile_height - image.height) // 2))
        draw_outlined_text(draw, (x, y + 6), caption, font=font, stroke=1)

    return sheet


def _scale_to_height(image: Image.Image, height: int) -> Image.Image:
    if image.height == height:
        return image
    width = max(1, round(image.width * height / image.height))
    return image.resize((width, height), Image.LANCZOS)


def _scale_to_width(image: Image.Image, width: int) -> Image.Image:
    if image.width == width:
        return image
    height = max(1, round(image.height * width / image.width))
    return image.resize((width, height), Image.LANCZOS)
