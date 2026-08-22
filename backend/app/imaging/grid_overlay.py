"""Draw the labelled grid the Scanner reads coordinates off.

Labels must survive any background — white text, black stroke, drawn in each
cell's top-left corner. Grid lines are deliberately semi-transparent so they
guide the model without hiding the defects it is looking for.
"""

from PIL import Image, ImageDraw

from app.domain.grid import Grid, cell_ref
from app.imaging.canvas import draw_outlined_text, font_for

LINE_COLOR = (255, 255, 255, 90)
LINE_WIDTH = 1
LABEL_INSET = 3


def apply_grid(image: Image.Image, grid: Grid | None = None) -> Image.Image:
    """Return a copy of ``image`` with the labelled grid drawn over it."""
    grid = grid or Grid.for_image(image.width, image.height)
    if (grid.width, grid.height) != image.size:
        raise ValueError(
            f"grid is {grid.width}x{grid.height}, image is {image.width}x{image.height}"
        )

    base = image.convert("RGBA")
    lines = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(lines)

    for x in grid.x_edges():
        draw.line([(x, 0), (x, grid.height)], fill=LINE_COLOR, width=LINE_WIDTH)
    for y in grid.y_edges():
        draw.line([(0, y), (grid.width, y)], fill=LINE_COLOR, width=LINE_WIDTH)

    composed = Image.alpha_composite(base, lines).convert("RGB")
    _draw_labels(composed, grid)
    return composed


def _draw_labels(image: Image.Image, grid: Grid) -> None:
    draw = ImageDraw.Draw(image)
    cell_height = grid.height / grid.rows
    font = font_for(max(10, min(22, int(cell_height * 0.22))))

    for row in range(grid.rows):
        for col in range(grid.cols):
            ref = cell_ref(col, row)
            box = grid.cell_bounds(ref)
            draw_outlined_text(
                draw, (box.left + LABEL_INSET, box.top + LABEL_INSET), ref, font=font
            )
