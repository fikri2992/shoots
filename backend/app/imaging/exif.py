"""EXIF → ``entities.Exif``. Hard evidence for the Judge, so this is strict.

Phones, exports and manual lenses leave holes: missing tags, zero values
(``FNumber=0`` on an adapted manual lens), rationals. Anything absent or zero
becomes ``None``; the Judge treats ``None`` as "cannot check", never as a pass.
"""

import io
from datetime import datetime
from fractions import Fraction
from typing import Any

from PIL import ExifTags, Image

from app.domain.entities import Exif

_DATETIME_FORMATS = ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, tuple) and len(value) == 2:
            value = Fraction(int(value[0]), int(value[1]))
        number = float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    if number <= 0 or number != number:  # zero, negative, NaN
        return None
    return number


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="ignore")
    return str(value).strip().strip("\x00")


def _when(value: Any) -> datetime | None:
    text = _text(value)
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _flash(value: Any) -> bool | None:
    try:
        return bool(int(value) & 0x1)
    except (TypeError, ValueError):
        return None


def read_exif(data: bytes) -> Exif:
    """Parse from the original bytes; Pillow transforms can drop the block."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            root = image.getexif()
            detail = root.get_ifd(ExifTags.IFD.Exif)
            gps = root.get_ifd(ExifTags.IFD.GPSInfo)
    except Exception:
        return Exif()

    iso = detail.get(ExifTags.Base.ISOSpeedRatings)
    if isinstance(iso, tuple):
        iso = iso[0] if iso else None
    iso_value = _num(iso)

    focal35 = _num(detail.get(ExifTags.Base.FocalLengthIn35mmFilm))

    return Exif(
        make=_text(root.get(ExifTags.Base.Make)),
        model=_text(root.get(ExifTags.Base.Model)),
        lens=_text(detail.get(ExifTags.Base.LensModel)),
        exposure_time_s=_num(detail.get(ExifTags.Base.ExposureTime)),
        f_number=_num(detail.get(ExifTags.Base.FNumber)),
        iso=int(iso_value) if iso_value else None,
        focal_length_mm=_num(detail.get(ExifTags.Base.FocalLength)),
        focal_length_35mm=int(focal35) if focal35 else None,
        flash_fired=_flash(detail.get(ExifTags.Base.Flash)),
        captured_at=_when(detail.get(ExifTags.Base.DateTimeOriginal))
        or _when(root.get(ExifTags.Base.DateTime)),
        latitude=_coordinate(gps, 2, 1, "S"),
        longitude=_coordinate(gps, 4, 3, "W"),
    )


def _coordinate(gps, value_key: int, ref_key: int, negative: str) -> float | None:
    """Degrees/minutes/seconds plus a hemisphere letter to signed decimal degrees."""
    value = gps.get(value_key) if gps else None
    if not value or len(value) != 3:
        return None
    try:
        degrees, minutes, seconds = (float(v) for v in value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    out = degrees + minutes / 60 + seconds / 3600
    ref = gps.get(ref_key)
    if isinstance(ref, bytes):
        ref = ref.decode(errors="ignore")
    if str(ref or "").upper().startswith(negative):
        out = -out
    return round(out, 6) if out else None
