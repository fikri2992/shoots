"""Crop a frame to a cell range. Cells in, pixels out, via ``domain/grid.py``."""

from PIL import Image

from app.domain.entities import GridSpec
from app.domain.grid import Grid

#: A crop narrower than this fraction of the frame is a detail, not a composition.
MIN_FRACTION = 0.2


def crop_to_cells(image: Image.Image, spec: GridSpec, cells: list[str]) -> Image.Image:
    """The smallest box covering ``cells``, scaled to this image's size."""
    grid = Grid(cols=spec.cols, rows=spec.rows, width=image.width, height=image.height)
    box = grid.span_bounds(cells)
    return image.crop((box.left, box.top, box.right, box.bottom))


def is_sensible(spec: GridSpec, cells: list[str]) -> bool:
    """Not the whole frame, not a sliver."""
    if not cells:
        return False
    grid = Grid(cols=spec.cols, rows=spec.rows, width=spec.width, height=spec.height)
    box = grid.span_bounds(cells)
    width = (box.right - box.left) / spec.width
    height = (box.bottom - box.top) / spec.height
    if width >= 0.98 and height >= 0.98:
        return False
    return width >= MIN_FRACTION and height >= MIN_FRACTION
