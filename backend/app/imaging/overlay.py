"""Draw the Analyst's composition read on a frame: subject box, horizon line,
suggested crop and move arrows. Cells in, pixels out, via ``domain/grid.py``.

The frame may be a different size from the gridded image the model saw
(originals are larger); the grid spec scales because cells are fractions.
"""

import math

from PIL import Image, ImageDraw

from app.domain.entities import Composition, GridSpec
from app.domain.grid import Box, Grid
from app.imaging.canvas import draw_outlined_text, font_for

SUBJECT = (80, 200, 255)
HORIZON = (255, 220, 90)
CROP = (255, 255, 255)
MOVE = (255, 90, 90)


def render_overlay(image: Image.Image, spec: GridSpec, composition: Composition) -> Image.Image:
    out = image.convert("RGB").copy()
    grid = Grid(cols=spec.cols, rows=spec.rows, width=out.width, height=out.height)
    draw = ImageDraw.Draw(out, "RGBA")
    stroke = max(2, round(min(out.size) / 300))
    font = font_for(max(14, round(min(out.size) / 45)))

    if composition.suggested_crop_cells:
        box = grid.span_bounds(composition.suggested_crop_cells)
        _dim_outside(out, box)
        draw = ImageDraw.Draw(out, "RGBA")
        draw.rectangle(box.as_tuple(), outline=CROP + (220,), width=stroke)
        draw_outlined_text(draw, (box.left + 8, box.top + 6), "suggested crop", font=font)

    if composition.horizon_row is not None and 1 <= composition.horizon_row <= grid.rows:
        y = round((composition.horizon_row - 0.5) * out.height / grid.rows)
        draw.line([(0, y), (out.width, y)], fill=HORIZON + (200,), width=stroke)
        draw_outlined_text(draw, (8, y + 6), "horizon", font=font)

    if composition.subject_cells:
        box = grid.span_bounds(composition.subject_cells)
        draw.rectangle(box.as_tuple(), outline=SUBJECT + (230,), width=stroke)
        draw_outlined_text(draw, (box.left + 8, box.top + 6), "subject", font=font)

    for index, move in enumerate(composition.moves, 1):
        if not (move.from_cells and move.to_cells):
            continue
        start = grid.span_bounds(move.from_cells).center
        end = grid.span_bounds(move.to_cells).center
        _arrow(draw, start, end, stroke)
        draw_outlined_text(draw, (end[0] + 10, end[1] - 10), f"{index}. {move.what}", font=font)

    return out


def _dim_outside(image: Image.Image, box: Box) -> None:
    shade = Image.new("RGB", image.size, (0, 0, 0))
    mask = Image.new("L", image.size, 110)
    ImageDraw.Draw(mask).rectangle(box.as_tuple(), fill=0)
    image.paste(Image.composite(shade, image, mask))


def _arrow(
    draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], stroke: int
) -> None:
    draw.line([start, end], fill=MOVE + (240,), width=stroke)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head = stroke * 6
    left = (end[0] - head * math.cos(angle - 0.5), end[1] - head * math.sin(angle - 0.5))
    right = (end[0] - head * math.cos(angle + 0.5), end[1] - head * math.sin(angle + 0.5))
    draw.polygon([end, left, right], fill=MOVE + (240,))
    draw.ellipse(
        (
            start[0] - stroke * 2,
            start[1] - stroke * 2,
            start[0] + stroke * 2,
            start[1] + stroke * 2,
        ),
        fill=MOVE + (240,),
    )
