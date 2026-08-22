"""EXIF reader against JPEGs Pillow actually wrote. Hard evidence must be exact."""

from datetime import UTC, datetime

from app.imaging.exif import read_exif
from tests.fixtures import jpeg_with_exif


def test_reads_the_fields_the_judge_uses():
    exif = read_exif(jpeg_with_exif(exposure=(1, 30), f_number=(56, 10), iso=200, focal=(50, 1)))
    assert exif.exposure_time_s == 1 / 30
    assert exif.f_number == 5.6
    assert exif.iso == 200
    assert exif.focal_length_mm == 50
    assert exif.focal_length_35mm == 75
    assert exif.flash_fired is False
    assert exif.make == "TestCam" and exif.model == "T1"
    assert exif.lens == "Test 50mm f/1.8"
    assert exif.captured_at == datetime(2026, 8, 22, 18, 30, tzinfo=UTC)


def test_long_exposure_and_flash():
    exif = read_exif(jpeg_with_exif(exposure=(30, 1), flash=1))
    assert exif.exposure_time_s == 30
    assert exif.flash_fired is True


def test_zero_means_unknown_not_f_zero():
    # Adapted manual lenses report FNumber=0 and FocalLength=0.
    exif = read_exif(jpeg_with_exif(f_number=(0, 1), focal=(0, 1), focal35=0))
    assert exif.f_number is None
    assert exif.focal_length_mm is None
    assert exif.focal_length_35mm is None
    assert exif.exposure_time_s == 1 / 30  # the rest still reads


def test_no_exif_is_all_none():
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (64, 64)).save(buffer, format="PNG")
    exif = read_exif(buffer.getvalue())
    assert exif.exposure_time_s is None and exif.f_number is None and exif.iso is None
    assert exif.captured_at is None


def test_garbage_bytes_do_not_raise():
    assert read_exif(b"not an image") == read_exif(b"")


def test_reads_gps_as_signed_degrees():
    exif = read_exif(jpeg_with_exif(gps=(-6.8436, 107.6123)))
    assert exif.latitude is not None and abs(exif.latitude + 6.8436) < 1e-4
    assert exif.longitude is not None and abs(exif.longitude - 107.6123) < 1e-4
    assert read_exif(jpeg_with_exif()).latitude is None
