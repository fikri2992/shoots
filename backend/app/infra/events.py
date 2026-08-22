"""In-process pub/sub feeding the live agent activity feed over SSE.

Subscribers are per-connection queues keyed by project. A slow or vanished client
must never block the pipeline, so publishing to a full queue drops the oldest event
rather than waiting — the feed is a live view, not an audit log. The durable record
of what happened is in Firestore.
"""

import asyncio
import contextlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.domain.entities import now

MAX_QUEUED_EVENTS = 256


@dataclass
class Event:
    stage: str
    detail: dict[str, Any] = field(default_factory=dict)
    project_id: str = ""
    run_id: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "detail": self.detail,
            "run_id": self.run_id,
            "at": now().isoformat(),
        }


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[Event]]] = defaultdict(list)

    def subscribe(self, project_id: str) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=MAX_QUEUED_EVENTS)
        self._subscribers[project_id].append(queue)
        return queue

    def unsubscribe(self, project_id: str, queue: asyncio.Queue[Event]) -> None:
        subscribers = self._subscribers.get(project_id, [])
        if queue in subscribers:
            subscribers.remove(queue)
        if not subscribers:
            self._subscribers.pop(project_id, None)

    def subscriber_count(self, project_id: str) -> int:
        return len(self._subscribers.get(project_id, []))

    async def publish(self, event: Event) -> None:
        for queue in list(self._subscribers.get(event.project_id, [])):
            _offer(queue, event)


def _offer(queue: asyncio.Queue[Event], event: Event) -> None:
    """Never block the producer. Drop the oldest event if a consumer has stalled."""
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        with contextlib.suppress(asyncio.QueueFull):
            queue.put_nowait(event)


#: One bus per process. Cloud Run may run several instances, so a client watching a
#: run started on another instance would not see its events; the review screen falls
#: back to polling the run's stored status. Documented rather than hidden.
bus = EventBus()
