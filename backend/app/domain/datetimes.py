"""Compatibility rules for ordering persisted timestamps."""

from datetime import UTC, datetime


def as_utc(value: datetime) -> datetime:
    """Return one comparable UTC instant.

    Legacy camera rows can lack an offset. Their original zone cannot be
    recovered, so the existing compatibility rule treats that wall time as
    UTC. New rows keep their recorded offset and are converted normally.
    """
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
