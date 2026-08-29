"""Small process-local gates for expensive service stages.

Pub/Sub owns the durable backlog. A gate only controls how much work one
Cloud Run process admits at once; it never becomes another source of truth.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class StageGate:
    """Bound concurrent entries while exposing honest local counts."""

    def __init__(self, limit: int) -> None:
        if limit < 1:
            raise ValueError("stage gate limit must be positive")
        self.limit = limit
        self.active = 0
        self.waiting = 0
        self._semaphore = asyncio.Semaphore(limit)

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        self.waiting += 1
        try:
            await self._semaphore.acquire()
        except BaseException:
            self.waiting -= 1
            raise
        self.waiting -= 1
        self.active += 1
        try:
            yield
        finally:
            self.active -= 1
            self._semaphore.release()
