"""Draw the read on a frame, the way a photographer reads a frame.

Three layers, in this order and in this order of loudness:

1. **Guide** — thirds, phi, the diagonal method, a centre axis: thin, dim,
   unlabelled. Chosen by the technique the panel agreed on (``domain/guides``),
   never the model's cell mesh, which is an addressing system and not a
   compositional idea.
2. **Findings** — what the panel saw: the subject, the horizon. Thin.
3. **One instruction** — a crop dims what leaves; a move draws a ghost box at
   the destination and one arrow; a camera change draws nothing at all,
   because a change of viewpoint has no honest mark on a flat image.

Cells in, pixels out, via ``domain/grid.py``. The frame may be a different
size from the gridded image the model saw; the grid spec scales because cells
are fractions.
"""

import math

from PIL import Image, ImageDraw

from app.domain import guides
from app.domain.entities import Composition, GridSpec, MoveKind
from app.domain.grid import Box, Grid
from app.imaging.canvas import draw_outlined_text, font_for

SUBJECT = (80, 200, 255)
HORIZON = (255, 220, 90)
CROP = (255, 255, 255)
MOVE = (255, 90, 90)
GUIDE = (255, 255, 255)
GUIDE_ALPHA = 90
PHI = 0.382  # 1 : 0.618 : 1, as a fraction of the whole


def render_overlay(image: Image.Image, spec: GridSpec, composition: Composition) -> Image.Image:
    out = image.convert("RGB").copy()
    grid = Grid(cols=spec.cols, rows=spec.rows, width=out.width, height=out.height)
    draw = ImageDraw.Draw(out, "RGBA")
    stroke = max(2, round(min(out.size) / 300))
    font = font_for(max(14, round(min(out.size) / 45)))

    _draw_guide(draw, out.size, composition.guide or guides.FALLBACK, stroke)
    _draw_subject_point(draw, out.size, composition, stroke)

    if composition.horizon_row is not None and 1 <= composition.horizon_row <= grid.rows:
        y = round((composition.horizon_row - 0.5) * out.height / grid.rows)
        draw.line([(0, y), (out.width, y)], fill=HORIZON + (170,), width=stroke)

    # The subject box steps aside for a crop: two rectangles over one frame
    # read as an argument. The subject dot still says where the centre landed.
    if composition.subject_cells and not composition.suggested_crop_cells:
        box = grid.span_bounds(composition.subject_cells)
        draw.rectangle(box.as_tuple(), outline=SUBJECT + (200,), width=stroke)

    # One instruction, and only one: the crop if there is one, otherwise the
    # first move that is actually a move.
    if composition.suggested_crop_cells:
        box = grid.span_bounds(composition.suggested_crop_cells)
        _dim_outside(out, box)
        draw = ImageDraw.Draw(out, "RGBA")
        draw.rectangle(box.as_tuple(), outline=CROP + (230,), width=stroke)
        draw_outlined_text(draw, (box.left + 8, box.top + 6), "crop to here", font=font)
        return out

    move = next((m for m in composition.moves if m.kind is MoveKind.MOVE), None)
    if move and move.from_cells and move.to_cells:
        start = grid.span_bounds(move.from_cells)
        end = grid.span_bounds(move.to_cells)
        draw.rectangle(end.as_tuple(), outline=MOVE + (150,), width=stroke)
        _arrow(draw, start.center, end.center, stroke)
        draw_outlined_text(draw, (end.left + 8, end.top + 6), move.what, font=font)

    return out


def _draw_guide(draw: ImageDraw.ImageDraw, size: tuple[int, int], guide: str, stroke: int) -> None:
    """The photographer's guide: thin, dim, unlabelled, always behind."""
    width, height = size
    fill = GUIDE + (GUIDE_ALPHA,)
    line = max(1, stroke // 2)

    if guide == guides.NONE or guide == guides.FILL:
        return
    if guide == guides.CENTRE:
        draw.line([(width // 2, 0), (width // 2, height)], fill=fill, width=line)
        draw.line([(0, height // 2), (width, height // 2)], fill=fill, width=line)
        return
    if guide == guides.DIAGONALS:
        # The diagonal method: corner-to-corner bisectors of each corner.
        short = min(width, height)
        corners = ((0, 0, 1, 1), (width, 0, -1, 1), (0, height, 1, -1), (width, height, -1, -1))
        for x0, y0, sx, sy in corners:
            draw.line([(x0, y0), (x0 + sx * short, y0 + sy * short)], fill=fill, width=line)
        draw.line([(0, 0), (width, height)], fill=fill, width=line)
        draw.line([(width, 0), (0, height)], fill=fill, width=line)
        return

    fractions = (PHI, 1 - PHI) if guide == guides.PHI else (1 / 3, 2 / 3)
    for fraction in fractions:
        x = round(width * fraction)
        y = round(height * fraction)
        draw.line([(x, 0), (x, height)], fill=fill, width=line)
        draw.line([(0, y), (width, y)], fill=fill, width=line)
    for fx in fractions:
        for fy in fractions:
            point = (round(width * fx), round(height * fy))
            radius = stroke * 2
            draw.ellipse(
                (point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius),
                outline=GUIDE + (150,),
                width=line,
            )


def _draw_subject_point(
    draw: ImageDraw.ImageDraw, size: tuple[int, int], composition: Composition, stroke: int
) -> None:
    """Where the subject's centre actually landed. A guide is only useful if
    you can see whether the frame is sitting on it."""
    if composition.subject_x is None or composition.subject_y is None:
        return
    x = round(size[0] * composition.subject_x)
    y = round(size[1] * composition.subject_y)
    radius = stroke * 3
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=SUBJECT + (230,))


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
