"""A stored blob must come back as the type it is, or the browser downloads it."""

import pytest

from app.infra.storage import content_type_for, extension_for, sniff

JPEG = bytes.fromhex("ffd8ff") + b"rest"
PNG = bytes.fromhex("89504e470d0a1a0a") + b"rest"
AVIF = b"\x00\x00\x00\x20ftypavif" + b"rest"
HEIC = b"\x00\x00\x00\x20ftypheic" + b"rest"
MP4 = b"\x00\x00\x00\x20ftypisom" + b"rest"
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"rest"


@pytest.mark.parametrize(
    "mime,extension",
    [
        ("image/jpeg", "jpg"),
        ("image/avif", "avif"),
        ("image/png", "png"),
        ("video/mp4", "mp4"),
        ("image/jpeg; charset=binary", "jpg"),
        ("IMAGE/JPEG", "jpg"),
        ("application/pdf", "bin"),
        ("", "bin"),
    ],
)
def test_extension_for(mime, extension):
    assert extension_for(mime) == extension


@pytest.mark.parametrize(
    "data,mime",
    [
        (JPEG, "image/jpeg"),
        (PNG, "image/png"),
        (AVIF, "image/avif"),
        (HEIC, "image/heic"),
        (MP4, "video/mp4"),
        (WEBP, "image/webp"),
        (b"nothing", "application/octet-stream"),
    ],
)
def test_sniff(data, mime):
    assert sniff(data) == mime


def test_extension_decides_when_it_knows():
    assert content_type_for("a/b/original.avif", b"") == "image/avif"
    assert content_type_for("a/b/thumb.jpeg", b"") == "image/jpeg"


def test_bytes_decide_for_blobs_written_before_the_map_covered_them():
    """The ten AVIF originals already on disk are named ``original.bin``."""
    assert content_type_for("a/b/original.bin", AVIF) == "image/avif"
    assert content_type_for("a/b/original.bin", b"") == "application/octet-stream"


def test_every_extension_maps_back_to_its_type():
    from app.infra.storage import EXTENSIONS

    for mime, extension in EXTENSIONS.items():
        assert content_type_for(f"x.{extension}") == mime
