"""Contact sheets: context and detail in one frame.

The Inspector is shown the whole image beside the zoomed crop so it can judge a
defect without losing track of what the picture is supposed to be. Panels are
captioned because an uncaptioned pair invites the model to confuse the two.
"""

from PIL import Image, ImageDraw

from app.domain.grid import Box
from app.imaging.canvas import draw_outlined_text, font_for

BACKGROUND = (18, 18, 18)
CAPTION_BAR = 34
GUTTER = 12
PADDING = 12


def contact_sheet(panels: list[tuple[str, Image.Image]], panel_height: int = 720) -> Image.Image:
    """Lay captioned panels out in a row, each scaled to a common height."""
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


def inspection_sheet(
    original: Image.Image,
    zoomed: Image.Image,
    refs: list[str],
    panel_height: int = 720,
    locator: Box | None = None,
) -> Image.Image:
    """The standard Inspector input: full frame beside the suspect region.

    When ``locator`` is given, the context panel is marked with the region the
    zoom was taken from, so the model does not have to infer the correspondence
    between the two panels — it can see it.
    """
    label = ", ".join(refs)
    context = highlight_region(original, locator) if locator else original
    return contact_sheet(
        [("FULL IMAGE (context)", context), (f"ZOOM: {label}", zoomed)],
        panel_height=panel_height,
    )


def highlight_region(image: Image.Image, box: Box) -> Image.Image:
    """Dim everything outside ``box`` and outline it, without hiding any content."""
    base = image.convert("RGB").copy()

    shade = Image.new("RGB", base.size, (0, 0, 0))
    mask = Image.new("L", base.size, 130)
    ImageDraw.Draw(mask).rectangle(box.as_tuple(), fill=0)
    base = Image.composite(shade, base, mask)

    width = max(2, round(min(base.size) / 250))
    draw = ImageDraw.Draw(base)
    draw.rectangle(box.as_tuple(), outline=(255, 255, 255), width=width)
    return base


def _scale_to_height(image: Image.Image, height: int) -> Image.Image:
    if image.height == height:
        return image
    width = max(1, round(image.width * height / image.height))
    return image.resize((width, height), Image.LANCZOS)
