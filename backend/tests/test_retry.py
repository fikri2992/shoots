"""Retry policy: what gets retried, what does not, and how long we wait.

The classification is tested against the actual error strings the Google SDK
produces, because it raises one exception type for nearly everything — the class
alone does not distinguish "slow down" from "that model does not exist".
"""

import asyncio

import pytest

from app.agents.retry import backoff_seconds, is_transient, with_retry
from app.config import settings

# Real messages seen from google-genai during this project.
QUOTA_429 = (
    "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': "
    "'Resource has been exhausted (e.g. check quota).', 'status': 'RESOURCE_EXHAUSTED'}}"
)
MODEL_404 = (
    "404 NOT_FOUND. {'error': {'code': 404, 'message': 'Publisher model "
    "`projects/x/locations/us-central1/publishers/google/models/gemini-3.1-pro` was not found'}}"
)
REGION_400 = (
    "400 FAILED_PRECONDITION. {'error': {'code': 400, 'message': "
    "'Precondition check failed.', 'status': 'FAILED_PRECONDITION'}}"
)
NO_KEY = "No API key was provided. Please pass a valid API key."


@pytest.fixture(autouse=True)
def fast_backoff(monkeypatch):
    """Keep the suite fast. The delays themselves are tested directly below,
    against explicit base values rather than the configured one."""
    monkeypatch.setattr(settings, "model_retry_base_seconds", 0.001)
    monkeypatch.setattr(settings, "model_retry_max_seconds", 0.01)


# --- classification -------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        QUOTA_429,
        "503 UNAVAILABLE. The service is currently unavailable.",
        "500 INTERNAL. Internal error encountered.",
        "504 DEADLINE_EXCEEDED",
        "Connection reset by peer",
    ],
)
def test_transient_failures_are_retried(message):
    assert is_transient(Exception(message)) is True


@pytest.mark.parametrize(
    "message",
    [
        MODEL_404,
        REGION_400,
        "401 UNAUTHENTICATED. Request had invalid authentication credentials.",
        "403 PERMISSION_DENIED. Vertex AI API has not been used in project",
        "400 INVALID_ARGUMENT. Request contains an invalid argument.",
    ],
)
def test_permanent_failures_are_not_retried(message):
    """Retrying a wrong model id or a missing permission only burns quota."""
    assert is_transient(Exception(message)) is False


def test_a_permanent_code_wins_over_a_transient_word():
    """A 400 whose text happens to contain 'internal' is still a 400."""
    assert is_transient(Exception("400 INVALID_ARGUMENT: internal parsing failure")) is False


def test_network_errors_are_transient():
    assert is_transient(TimeoutError("timed out")) is True
    assert is_transient(ConnectionError("connection aborted")) is True


def test_cancellation_is_never_retried():
    """A cancelled run is a deliberate shutdown, not a failure to wait out."""
    assert is_transient(asyncio.CancelledError()) is False


def test_an_unrecognised_error_is_not_retried():
    """Unknown means unknown — do not burn quota guessing."""
    assert is_transient(ValueError("something odd happened")) is False


# --- backoff --------------------------------------------------------------


def test_backoff_grows_exponentially(monkeypatch):
    monkeypatch.setattr(settings, "model_retry_max_seconds", 30.0)
    first = backoff_seconds(1, base=2.0, jitter=0.0)
    second = backoff_seconds(2, base=2.0, jitter=0.0)
    third = backoff_seconds(3, base=2.0, jitter=0.0)
    assert (first, second, third) == (2.0, 4.0, 8.0)


def test_backoff_is_capped(monkeypatch):
    monkeypatch.setattr(settings, "model_retry_max_seconds", 30.0)
    assert backoff_seconds(20, base=2.0, jitter=0.0) == 30.0


def test_jitter_spreads_concurrent_retries(monkeypatch):
    """Without jitter every fanned-out call would retry in lockstep and 429 together."""
    monkeypatch.setattr(settings, "model_retry_max_seconds", 30.0)
    delays = {backoff_seconds(2, base=2.0) for _ in range(50)}
    assert len(delays) > 40, "delays are not being jittered"
    assert all(3.0 <= d <= 5.0 for d in delays)


def test_jitter_never_produces_a_negative_delay():
    assert all(backoff_seconds(1, base=0.01) >= 0 for _ in range(100))


# --- the retry loop -------------------------------------------------------


async def test_a_successful_call_is_not_retried():
    calls = 0

    async def call():
        nonlocal calls
        calls += 1
        return "ok"

    assert await with_retry(call) == "ok"
    assert calls == 1


async def test_a_transient_failure_is_retried_until_it_succeeds():
    calls = 0

    async def call():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise Exception(QUOTA_429)
        return "ok"

    assert await with_retry(call, attempts=5) == "ok"
    assert calls == 3


async def test_a_permanent_failure_fails_immediately():
    calls = 0

    async def call():
        nonlocal calls
        calls += 1
        raise Exception(MODEL_404)

    with pytest.raises(Exception, match="NOT_FOUND"):
        await with_retry(call, attempts=5)
    assert calls == 1, "a permanent failure must not be retried"


async def test_attempts_are_bounded():
    calls = 0

    async def call():
        nonlocal calls
        calls += 1
        raise Exception(QUOTA_429)

    with pytest.raises(Exception, match="RESOURCE_EXHAUSTED"):
        await with_retry(call, attempts=3)
    assert calls == 3


async def test_the_original_error_survives_the_retries():
    """Callers must see which quota gave out, not a generic wrapper."""

    async def call():
        raise Exception(QUOTA_429)

    with pytest.raises(Exception) as caught:
        await with_retry(call, attempts=2)
    assert "check quota" in str(caught.value)


async def test_the_caller_is_told_about_each_retry():
    seen = []

    async def call():
        if len(seen) < 2:
            raise Exception(QUOTA_429)
        return "ok"

    await with_retry(
        call, attempts=5, on_retry=lambda attempt, delay, error: seen.append((attempt, delay))
    )

    assert [attempt for attempt, _ in seen] == [1, 2]
    assert all(delay > 0 for _, delay in seen)


async def test_cancellation_propagates_without_retrying():
    calls = 0

    async def call():
        nonlocal calls
        calls += 1
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await with_retry(call, attempts=5)
    assert calls == 1


async def test_a_single_attempt_means_no_retry():
    calls = 0

    async def call():
        nonlocal calls
        calls += 1
        raise Exception(QUOTA_429)

    with pytest.raises(Exception, match="RESOURCE_EXHAUSTED"):
        await with_retry(call, attempts=1)
    assert calls == 1
