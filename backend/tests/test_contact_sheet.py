"""Tile sheet geometry on real Pillow output."""

import pytest
from PIL import Image

from app.imaging.contact_sheet import CAPTION_BAR, GUTTER, PADDING, tile_sheet


def _frames(n: int, size=(640, 360)) -> list[tuple[str, Image.Image]]:
    return [(f"0:0{i}", Image.new("RGB", size, (i * 20, 100, 150))) for i in range(n)]


def test_full_rows_have_expected_size():
    sheet = tile_sheet(_frames(8), cols=4, tile_width=480)
    tile_h = round(360 * 480 / 640)
    assert sheet.width == PADDING * 2 + 4 * 480 + 3 * GUTTER
    assert sheet.height == PADDING * 2 + 2 * (CAPTION_BAR + tile_h) + GUTTER


def test_partial_last_row_and_fewer_than_cols():
    sheet = tile_sheet(_frames(3), cols=4, tile_width=200)
    assert sheet.width == PADDING * 2 + 3 * 200 + 2 * GUTTER  # only 3 columns used
    single = tile_sheet(_frames(1), cols=4, tile_width=200)
    assert single.width == PADDING * 2 + 200


def test_mixed_orientation_tiles_align():
    panels = [("a", Image.new("RGB", (640, 360))), ("b", Image.new("RGB", (360, 640)))]
    sheet = tile_sheet(panels, cols=2, tile_width=300)
    tallest = round(640 * 300 / 360)
    assert sheet.height == PADDING * 2 + CAPTION_BAR + tallest


def test_tile_pixels_land_where_computed():
    sheet = tile_sheet(_frames(2), cols=2, tile_width=100)
    tile_h = round(360 * 100 / 640)
    # Centre of the second tile's image area should be that frame's colour.
    x = PADDING + 100 + GUTTER + 50
    y = PADDING + CAPTION_BAR + tile_h // 2
    assert sheet.getpixel((x, y)) == (20, 100, 150)


def test_empty_and_bad_cols_raise():
    with pytest.raises(ValueError):
        tile_sheet([])
    with pytest.raises(ValueError):
        tile_sheet(_frames(1), cols=0)
