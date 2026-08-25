"""Idempotent on cost, not only on write.

The stage spends four to six model calls before it writes anything, so a
failure after the panel returned used to leave the shot at INGESTED and the
redelivery paid for the panel again — five times over, at the transport's
attempt limit.
"""

from datetime import timedelta

from app.domain.entities import Shot, ShotKind, ShotStatus, now
from app.services.analyst import _LEASE_SECONDS, _in_flight


def photo_shot() -> Shot:
    return Shot(
        id="shot_1",
        user_id="u1",
        drive_file_id="f1",
        filename="bike.jpg",
        mime_type="image/jpeg",
        kind=ShotKind.PHOTO,
    )


def claimed(seconds_ago: float) -> Shot:
    shot = photo_shot()
    shot.status = ShotStatus.ANALYSING
    shot.analysing_at = now() - timedelta(seconds=seconds_ago)
    return shot


def test_a_fresh_claim_is_believed():
    """Someone else is mid-panel. Paying for a second one buys nothing."""
    assert _in_flight(claimed(5)) is True


def test_a_stale_claim_is_taken_over():
    """Nothing is coming to clear it: that worker died. The lease is the
    panel's own timeout plus room for everything after it."""
    assert _in_flight(claimed(_LEASE_SECONDS + 1)) is False


def test_the_lease_outlasts_a_panel_that_runs_to_its_timeout():
    from app.config import settings

    assert settings.panel_timeout_seconds < _LEASE_SECONDS


def test_a_claim_with_no_date_is_not_believed():
    """Written by an older version, or by hand. Better to re-analyse than to
    strand the shot forever."""
    shot = photo_shot()
    shot.status = ShotStatus.ANALYSING
    shot.analysing_at = None
    assert _in_flight(shot) is False


def test_the_other_statuses_are_not_leases():
    for status in (ShotStatus.NEW, ShotStatus.INGESTED, ShotStatus.ANALYZED, ShotStatus.FAILED):
        shot = photo_shot()
        shot.status = status
        shot.analysing_at = now()
        assert _in_flight(shot) is False
