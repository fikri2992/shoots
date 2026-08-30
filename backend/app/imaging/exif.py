"""EXIF → ``entities.Exif``. Hard evidence for the Judge, so this is strict.

Phones, exports and manual lenses leave holes: missing tags, zero values
(``FNumber=0`` on an adapted manual lens), rationals. Anything absent or zero
becomes ``None``; the Judge treats ``None`` as "cannot check", never as a pass.
"""

import io
import math
import re
from datetime import UTC, datetime, timedelta, timezone
from fractions import Fraction
from typing import Any

from PIL import ExifTags, Image

from app.domain.entities import CaptureTimeAuthority, Exif

_DATETIME_FORMATS = ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")
_OFFSET = re.compile(r"^([+-])(\d{2}):(\d{2})$")


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


def _utc_offset_minutes(value: Any) -> int | None:
    match = _OFFSET.fullmatch(_text(value))
    if match is None:
        return None
    hours, minutes = int(match.group(2)), int(match.group(3))
    if hours > 14 or minutes >= 60 or (hours == 14 and minutes):
        return None
    total = hours * 60 + minutes
    return -total if match.group(1) == "-" else total


def _when(value: Any, utc_offset_minutes: int | None = None) -> datetime | None:
    """Parse the wall clock while keeping unknown timezone authority explicit.

    Legacy storage expects comparable aware datetimes, so a timezone-less wall
    clock keeps the old UTC carrier. ``capture_utc_offset_minutes`` tells every
    time-sensitive consumer that this carrier is not a known instant.
    """
    text = _text(value)
    for fmt in _DATETIME_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
            if utc_offset_minutes is None:
                return parsed.replace(tzinfo=UTC)
            zone = timezone(timedelta(minutes=utc_offset_minutes))
            return parsed.replace(tzinfo=zone).astimezone(UTC)
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

    original_offset = _utc_offset_minutes(detail.get(0x9011))
    original_time = _when(detail.get(ExifTags.Base.DateTimeOriginal), original_offset)
    fallback_offset = _utc_offset_minutes(root.get(0x9010))
    fallback_time = _when(root.get(ExifTags.Base.DateTime), fallback_offset)
    captured_at = original_time or fallback_time
    used_offset = original_offset if original_time is not None else fallback_offset

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
        captured_at=captured_at,
        capture_utc_offset_minutes=used_offset if captured_at is not None else None,
        capture_time_authority=(
            CaptureTimeAuthority.EXIF_OFFSET
            if captured_at is not None and used_offset is not None
            else CaptureTimeAuthority.UNKNOWN
        ),
        latitude=_coordinate(gps, 2, 1, "S", 90),
        longitude=_coordinate(gps, 4, 3, "W", 180),
    )


def _coordinate(gps, value_key: int, ref_key: int, negative: str, maximum: float) -> float | None:
    """Degrees/minutes/seconds plus a hemisphere letter to signed decimal degrees."""
    value = gps.get(value_key) if gps else None
    if not value or len(value) != 3:
        return None
    try:
        degrees, minutes, seconds = (float(v) for v in value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    if not all(math.isfinite(part) for part in (degrees, minutes, seconds)):
        return None
    if not (0 <= degrees <= maximum and 0 <= minutes < 60 and 0 <= seconds < 60):
        return None
    if degrees == maximum and (minutes or seconds):
        return None

    out = degrees + minutes / 60 + seconds / 3600
    ref = gps.get(ref_key)
    if isinstance(ref, bytes):
        ref = ref.decode(errors="ignore")
    hemisphere = str(ref or "").strip().upper()[:1]
    positive = "N" if negative == "S" else "E"
    if hemisphere not in {positive, negative}:
        return None
    if hemisphere == negative:
        out = -out
    return round(out, 6)
