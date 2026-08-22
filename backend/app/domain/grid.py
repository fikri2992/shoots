"""Grid geometry — the coordinate system the whole pipeline speaks.

Golden rule (AGENTS.md): models emit **cell refs**, never pixels. Everything here
converts between the two, so spatial reasoning stays inside tested pure code.

The grid is nominally 8x8 but adapts to aspect ratio so cells stay near-square:
a 16:9 image gets more columns, a 4:5 portrait more rows, both totalling ~64 cells.
Refs are chess-style: column letter + 1-based row number, ``A1`` top-left.
"""

import math
import re
from dataclasses import dataclass

TARGET_CELLS = 64
MIN_AXIS = 4
MAX_AXIS = 26  # bounded by single-letter column labels

_REF_PATTERN = re.compile(r"^([A-Z])(\d{1,2})$")


class GridError(ValueError):
    """Raised for malformed or out-of-range cell references."""


@dataclass(frozen=True)
class Box:
    """Pixel rectangle, left/top inclusive and right/bottom exclusive."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center(self) -> tuple[int, int]:
        return ((self.left + self.right) // 2, (self.top + self.bottom) // 2)

    def as_tuple(self) -> tuple[int, int, int, int]:
        """In PIL's crop/rectangle order."""
        return (self.left, self.top, self.right, self.bottom)


@dataclass(frozen=True)
class Grid:
    cols: int
    rows: int
    width: int
    height: int

    # --- construction -----------------------------------------------------

    @classmethod
    def for_image(cls, width: int, height: int, target_cells: int = TARGET_CELLS) -> "Grid":
        """Pick a near-square cell layout for this image's aspect ratio."""
        if width <= 0 or height <= 0:
            raise GridError(f"image must have positive dimensions, got {width}x{height}")

        aspect = width / height
        cols = _clamp(round(math.sqrt(target_cells * aspect)), MIN_AXIS, MAX_AXIS)
        rows = _clamp(round(target_cells / cols), MIN_AXIS, MAX_AXIS)
        return cls(cols=cols, rows=rows, width=width, height=height)

    # --- refs -------------------------------------------------------------

    @property
    def cell_count(self) -> int:
        return self.cols * self.rows

    def all_refs(self) -> list[str]:
        """Reading order: A1, B1, C1, ... then A2, B2, ..."""
        return [cell_ref(col, row) for row in range(self.rows) for col in range(self.cols)]

    def contains(self, ref: str) -> bool:
        try:
            self.parse(ref)
        except GridError:
            return False
        return True

    def parse(self, ref: str) -> tuple[int, int]:
        """``"C4"`` -> ``(2, 3)`` zero-based (col, row), validated against this grid."""
        col, row = parse_ref(ref)
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            raise GridError(f"{ref} is outside a {self.cols}x{self.rows} grid")
        return col, row

    # --- geometry ---------------------------------------------------------

    def cell_bounds(self, ref: str) -> Box:
        """Pixel box of one cell. Adjacent cells share edges exactly — no gaps."""
        col, row = self.parse(ref)
        return Box(
            left=self._x(col),
            top=self._y(row),
            right=self._x(col + 1),
            bottom=self._y(row + 1),
        )

    def span_bounds(self, refs: list[str]) -> Box:
        """Smallest box covering every ref — defects often straddle cells."""
        if not refs:
            raise GridError("no cells given")
        boxes = [self.cell_bounds(ref) for ref in refs]
        return Box(
            left=min(b.left for b in boxes),
            top=min(b.top for b in boxes),
            right=max(b.right for b in boxes),
            bottom=max(b.bottom for b in boxes),
        )

    def zoom_bounds(self, refs: list[str], margin_cells: int = 1) -> Box:
        """Span plus a margin of whole cells, clamped to the image.

        The margin exists because defects rarely respect cell boundaries — the
        Inspector needs to see just outside what the Scanner flagged.
        """
        if margin_cells < 0:
            raise GridError("margin must not be negative")

        cols_rows = [self.parse(ref) for ref in refs] or []
        if not cols_rows:
            raise GridError("no cells given")

        min_col = min(c for c, _ in cols_rows) - margin_cells
        max_col = max(c for c, _ in cols_rows) + margin_cells
        min_row = min(r for _, r in cols_rows) - margin_cells
        max_row = max(r for _, r in cols_rows) + margin_cells

        return Box(
            left=self._x(_clamp(min_col, 0, self.cols)),
            top=self._y(_clamp(min_row, 0, self.rows)),
            right=self._x(_clamp(max_col + 1, 0, self.cols)),
            bottom=self._y(_clamp(max_row + 1, 0, self.rows)),
        )

    def circle_for(self, refs: list[str], padding: float = 0.15) -> tuple[int, int, int]:
        """Initial annotation circle as ``(cx, cy, radius)``.

        The Annotator nudges this after looking at its own output; this is the
        opening guess, sized to enclose the flagged span with a little air.
        """
        box = self.span_bounds(refs)
        cx, cy = box.center
        radius = math.ceil(math.hypot(box.width, box.height) / 2 * (1 + padding))
        return cx, cy, max(radius, 1)

    def x_edges(self) -> list[int]:
        """Vertical grid line positions, including both outer edges."""
        return [self._x(col) for col in range(self.cols + 1)]

    def y_edges(self) -> list[int]:
        return [self._y(row) for row in range(self.rows + 1)]

    # --- internals --------------------------------------------------------

    def _x(self, col: int) -> int:
        return round(col * self.width / self.cols)

    def _y(self, row: int) -> int:
        return round(row * self.height / self.rows)


def cell_ref(col: int, row: int) -> str:
    """Zero-based ``(2, 3)`` -> ``"C4"``."""
    if not (0 <= col < MAX_AXIS):
        raise GridError(f"column {col} out of range")
    if row < 0:
        raise GridError(f"row {row} out of range")
    return f"{chr(ord('A') + col)}{row + 1}"


def parse_ref(ref: str) -> tuple[int, int]:
    """``"C4"`` -> ``(2, 3)``. Grid-agnostic; use ``Grid.parse`` to bounds-check."""
    match = _REF_PATTERN.match(ref.strip().upper())
    if not match:
        raise GridError(f"malformed cell ref: {ref!r}")
    letter, number = match.groups()
    row = int(number) - 1
    if row < 0:
        raise GridError(f"rows are 1-based: {ref!r}")
    return ord(letter) - ord("A"), row


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))
