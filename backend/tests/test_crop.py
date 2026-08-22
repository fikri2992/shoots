from PIL import Image

from app.domain.entities import GridSpec
from app.imaging.crop import crop_to_cells, is_sensible

SPEC = GridSpec(cols=8, rows=6, width=1600, height=1200)


def test_crop_scales_cells_to_the_image():
    image = Image.new("RGB", (800, 600), (1, 2, 3))  # half the spec's size
    out = crop_to_cells(image, SPEC, ["B2", "D4"])
    # cells are 100x100 on the 800x600 image; B2..D4 spans 3 cols x 3 rows
    assert out.size == (300, 300)


def test_sensible_rejects_whole_frame_and_slivers():
    assert is_sensible(SPEC, ["B2", "F5"])
    assert not is_sensible(SPEC, ["A1", "H6"])
    assert not is_sensible(SPEC, ["A1"])
    assert not is_sensible(SPEC, [])
