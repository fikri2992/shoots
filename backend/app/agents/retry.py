"""Retry policy for model calls.

Quota limits are not an edge case here: a batch of images fans out into scan,
inspect and annotate calls, and the image model 429s above roughly two concurrent
requests. Without backoff a demo dies mid-run.

The decision of *what* to retry is kept as a pure function so it can be tested
against real error shapes rather than by mocking a client.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable

from app.config import settings

#: Conditions worth waiting out — the request was fine, the service was not.
TRANSIENT_MARKERS = (
    "resource_exhausted",
    "429",
    "unavailable",
    "503",
    "internal",
    "500",
    "deadline_exceeded",
    "504",
    "connection reset",
    "connection aborted",
    "timed out",
)

#: Conditions where retrying only wastes quota — the request itself is wrong.
PERMANENT_MARKERS = (
    "invalid_argument",
    "400",
    "unauthenticated",
    "401",
    "permission_denied",
    "403",
    "not_found",
    "404",
    "failed_precondition",
)


def is_transient(error: BaseException) -> bool:
    """Whether waiting and trying again could plausibly succeed.

    Matched on the message because the SDK raises a single ``ClientError`` type for
    most failures, so the class alone does not distinguish "slow down" from
    "this model does not exist".
    """
    if isinstance(error, asyncio.CancelledError):
        return False
    if isinstance(error, TimeoutError | ConnectionError):
        return True

    message = str(error).lower()
    # Permanent wins: a 400 mentioning "internal" is still a 400.
    if any(marker in message for marker in PERMANENT_MARKERS):
        return False
    return any(marker in message for marker in TRANSIENT_MARKERS)


def backoff_seconds(attempt: int, base: float | None = None, jitter: float = 0.25) -> float:
    """Exponential backoff for a 1-based attempt number, with jitter.

    Jitter matters more than usual here: the orchestrator fans out concurrently, so
    without it every rate-limited call would retry in lockstep and 429 together.
    """
    base = settings.model_retry_base_seconds if base is None else base
    delay = base * (2 ** (attempt - 1))
    delay = min(delay, settings.model_retry_max_seconds)
    return delay * (1 + random.uniform(-jitter, jitter))


async def with_retry[T](
    call: Callable[[], Awaitable[T]],
    *,
    attempts: int | None = None,
    on_retry: Callable[[int, float, BaseException], None] | None = None,
) -> T:
    """Run ``call``, retrying transient failures with exponential backoff.

    The final failure is raised unchanged, so callers see the real error rather
    than a wrapper that hides which model or which quota gave out.
    """
    limit = settings.max_model_retries if attempts is None else attempts
    last: BaseException | None = None

    for attempt in range(1, limit + 1):
        try:
            return await call()
        except BaseException as error:  # noqa: BLE001 — re-raised below
            last = error
            if attempt == limit or not is_transient(error):
                raise
            delay = backoff_seconds(attempt)
            if on_retry:
                on_retry(attempt, delay, error)
            await asyncio.sleep(delay)

    assert last is not None  # unreachable: the loop either returns or raises
    raise last
