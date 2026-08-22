"""Grid geometry — Gate 1 requires exact cell->pixel mapping on 1:1, 4:5 and 16:9.

These are the tests that let the rest of the pipeline trust cell refs. Every
assertion is on real computed geometry; there is nothing to mock.
"""

import itertools

import pytest

from app.domain.grid import Box, Grid, GridError, cell_ref, parse_ref

#: (label, width, height) — the three aspect ratios Gate 1 names.
ASPECTS = [
    ("square", 1024, 1024),
    ("portrait_4_5", 1080, 1350),
    ("landscape_16_9", 1920, 1080),
]
ASPECT_IDS = [name for name, _, _ in ASPECTS]


@pytest.fixture(params=ASPECTS, ids=ASPECT_IDS)
def grid(request):
    _, width, height = request.param
    return Grid.for_image(width, height)


# --- ref parsing ----------------------------------------------------------


def test_cell_ref_round_trips_for_every_position():
    for col, row in itertools.product(range(26), range(20)):
        assert parse_ref(cell_ref(col, row)) == (col, row)


def test_known_refs():
    assert parse_ref("A1") == (0, 0)
    assert parse_ref("C4") == (2, 3)
    assert parse_ref("H8") == (7, 7)
    assert cell_ref(0, 0) == "A1"
    assert cell_ref(7, 7) == "H8"


def test_refs_are_case_and_whitespace_tolerant():
    assert parse_ref(" c4 ") == parse_ref("C4")


@pytest.mark.parametrize("bad", ["", "4C", "C0", "AA1", "C", "1", "C-1", "C 4", "😀1"])
def test_malformed_refs_are_rejected(bad):
    with pytest.raises(GridError):
        parse_ref(bad)


def test_out_of_range_refs_are_rejected_against_the_grid():
    grid = Grid(cols=8, rows=8, width=800, height=800)
    with pytest.raises(GridError, match="outside"):
        grid.parse("I1")
    with pytest.raises(GridError, match="outside"):
        grid.parse("A9")
    assert grid.contains("H8")
    assert not grid.contains("I9")


# --- layout ---------------------------------------------------------------


def test_square_image_gets_the_nominal_8x8():
    grid = Grid.for_image(1024, 1024)
    assert (grid.cols, grid.rows) == (8, 8)
    assert grid.cell_count == 64


def test_layout_adapts_to_aspect_ratio(grid):
    """Landscape gets more columns than rows; portrait the reverse."""
    if grid.width > grid.height:
        assert grid.cols > grid.rows
    elif grid.width < grid.height:
        assert grid.rows > grid.cols
    else:
        assert grid.cols == grid.rows


def test_cells_stay_near_square(grid):
    """The whole point of adapting: no stretched cells for the model to misjudge."""
    cell = grid.cell_bounds("A1")
    ratio = cell.width / cell.height
    assert 0.8 <= ratio <= 1.25, f"{grid.cols}x{grid.rows} gave cell ratio {ratio:.2f}"


def test_cell_count_stays_near_target(grid):
    assert 48 <= grid.cell_count <= 84


@pytest.mark.parametrize(("width", "height"), [(0, 100), (100, 0), (-5, 5)])
def test_degenerate_images_are_rejected(width, height):
    with pytest.raises(GridError):
        Grid.for_image(width, height)


def test_extreme_panorama_stays_within_label_bounds():
    grid = Grid.for_image(8000, 200)
    assert grid.cols <= 26  # single-letter labels only
    assert grid.rows >= 4
    assert all(grid.contains(ref) for ref in grid.all_refs())


# --- exact pixel mapping (Gate 1: 64/64 exact) ----------------------------


def test_every_cell_maps_to_a_valid_box(grid):
    refs = grid.all_refs()
    assert len(refs) == grid.cell_count

    for ref in refs:
        box = grid.cell_bounds(ref)
        assert box.width > 0 and box.height > 0
        assert 0 <= box.left < box.right <= grid.width
        assert 0 <= box.top < box.bottom <= grid.height


def test_cells_tile_the_image_with_no_gaps_or_overlaps(grid):
    """Summed cell areas must equal the image area exactly."""
    total = sum(
        grid.cell_bounds(ref).width * grid.cell_bounds(ref).height for ref in grid.all_refs()
    )
    assert total == grid.width * grid.height


def test_adjacent_cells_share_edges_exactly(grid):
    for row in range(grid.rows):
        for col in range(grid.cols - 1):
            left_box = grid.cell_bounds(cell_ref(col, row))
            right_box = grid.cell_bounds(cell_ref(col + 1, row))
            assert left_box.right == right_box.left

    for col in range(grid.cols):
        for row in range(grid.rows - 1):
            upper = grid.cell_bounds(cell_ref(col, row))
            lower = grid.cell_bounds(cell_ref(col, row + 1))
            assert upper.bottom == lower.top


def test_corners_anchor_to_the_image_edges(grid):
    top_left = grid.cell_bounds("A1")
    assert (top_left.left, top_left.top) == (0, 0)

    bottom_right = grid.cell_bounds(cell_ref(grid.cols - 1, grid.rows - 1))
    assert (bottom_right.right, bottom_right.bottom) == (grid.width, grid.height)


def test_grid_lines_match_cell_boundaries(grid):
    x_edges, y_edges = grid.x_edges(), grid.y_edges()
    assert len(x_edges) == grid.cols + 1
    assert len(y_edges) == grid.rows + 1
    assert x_edges[0] == 0 and x_edges[-1] == grid.width
    assert y_edges[0] == 0 and y_edges[-1] == grid.height
    assert x_edges == sorted(x_edges) and y_edges == sorted(y_edges)

    for col in range(grid.cols):
        assert grid.cell_bounds(cell_ref(col, 0)).left == x_edges[col]


def test_reading_order_is_left_to_right_then_top_to_bottom():
    grid = Grid(cols=3, rows=2, width=300, height=200)
    assert grid.all_refs() == ["A1", "B1", "C1", "A2", "B2", "C2"]


# --- spans ----------------------------------------------------------------


def test_span_of_one_cell_is_that_cell():
    grid = Grid(cols=8, rows=8, width=800, height=800)
    assert grid.span_bounds(["C4"]) == grid.cell_bounds("C4")


def test_span_covers_every_listed_cell():
    grid = Grid(cols=8, rows=8, width=800, height=800)
    assert grid.span_bounds(["C4", "D4"]) == Box(left=200, top=300, right=400, bottom=400)


def test_span_is_order_independent():
    grid = Grid(cols=8, rows=8, width=800, height=800)
    assert grid.span_bounds(["D5", "C4"]) == grid.span_bounds(["C4", "D5"])


def test_empty_span_is_an_error():
    grid = Grid(cols=8, rows=8, width=800, height=800)
    with pytest.raises(GridError, match="no cells"):
        grid.span_bounds([])


# --- zoom margins, including edge clamping (Gate 1) -----------------------


def test_zoom_adds_a_cell_of_margin_on_every_side():
    grid = Grid(cols=8, rows=8, width=800, height=800)
    assert grid.zoom_bounds(["C4"], margin_cells=1) == Box(left=100, top=200, right=400, bottom=500)


def test_zoom_is_larger_than_the_span_it_wraps(grid):
    ref = grid.all_refs()[len(grid.all_refs()) // 2]
    span = grid.span_bounds([ref])
    zoom = grid.zoom_bounds([ref], margin_cells=1)
    assert zoom.width > span.width and zoom.height > span.height


def test_zero_margin_equals_the_span(grid):
    ref = grid.all_refs()[0]
    assert grid.zoom_bounds([ref], margin_cells=0) == grid.span_bounds([ref])


def test_margin_clamps_at_the_top_left_corner():
    grid = Grid(cols=8, rows=8, width=800, height=800)
    box = grid.zoom_bounds(["A1"], margin_cells=1)
    assert (box.left, box.top) == (0, 0)
    assert (box.right, box.bottom) == (200, 200)


def test_margin_clamps_at_the_bottom_right_corner():
    grid = Grid(cols=8, rows=8, width=800, height=800)
    box = grid.zoom_bounds(["H8"], margin_cells=1)
    assert (box.right, box.bottom) == (800, 800)
    assert (box.left, box.top) == (600, 600)


def test_every_edge_cell_clamps_inside_the_image(grid):
    """No crop may ever run off the canvas — Pillow would silently pad it."""
    for ref in grid.all_refs():
        box = grid.zoom_bounds([ref], margin_cells=1)
        assert 0 <= box.left < box.right <= grid.width
        assert 0 <= box.top < box.bottom <= grid.height


def test_an_oversized_margin_yields_the_whole_image(grid):
    box = grid.zoom_bounds(["A1"], margin_cells=99)
    assert box == Box(0, 0, grid.width, grid.height)


def test_negative_margin_is_rejected(grid):
    with pytest.raises(GridError, match="negative"):
        grid.zoom_bounds(["A1"], margin_cells=-1)


# --- circles --------------------------------------------------------------


def test_circle_is_centred_on_the_span():
    grid = Grid(cols=8, rows=8, width=800, height=800)
    cx, cy, _ = grid.circle_for(["C4"])
    assert (cx, cy) == grid.cell_bounds("C4").center


def test_circle_encloses_the_flagged_span(grid):
    """A circle that does not cover the defect is a wrong annotation."""
    ref = grid.all_refs()[0]
    cx, cy, radius = grid.circle_for([ref])
    box = grid.span_bounds([ref])

    for corner in [(box.left, box.top), (box.right, box.bottom), (box.left, box.bottom)]:
        distance = ((corner[0] - cx) ** 2 + (corner[1] - cy) ** 2) ** 0.5
        assert distance <= radius


def test_circle_grows_with_the_span():
    grid = Grid(cols=8, rows=8, width=800, height=800)
    _, _, small = grid.circle_for(["C4"])
    _, _, large = grid.circle_for(["C4", "D5"])
    assert large > small


def test_circle_radius_is_always_positive(grid):
    for ref in grid.all_refs():
        assert grid.circle_for([ref])[2] >= 1


# --- Box ------------------------------------------------------------------


def test_box_reports_pil_ordering():
    assert Box(1, 2, 5, 9).as_tuple() == (1, 2, 5, 9)
    assert Box(1, 2, 5, 9).width == 4
    assert Box(1, 2, 5, 9).height == 7
    assert Box(0, 0, 10, 10).center == (5, 5)
