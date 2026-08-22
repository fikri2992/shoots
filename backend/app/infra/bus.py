"""Stage transport. The pipeline is a chain of stages keyed by topic name:

    media.new → ingest → media.ingested → analyst → media.analyzed → ...

``InProcessBus`` runs the next stage as a task in this process, which is how
local development and the test suite work. ``PubSubBus`` publishes to Cloud
Pub/Sub and the push subscriptions call ``/pubsub/<stage>`` on Cloud Run.
Handlers are registered once, the same way, against either bus, so transport
never changes behaviour (decision 7).

Messages are small: ids only. A stage re-reads what it needs from the store,
which keeps every stage idempotent and replayable from the dead-letter topic.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from app.config import settings

logger = logging.getLogger(__name__)

Message = dict[str, Any]
Handler = Callable[[Message], Awaitable[None]]


@runtime_checkable
class Bus(Protocol):
    def subscribe(self, topic: str, handler: Handler) -> None: ...

    async def publish(self, topic: str, message: Message) -> None: ...


class InProcessBus:
    """Handlers run as background tasks; publish never waits for them.

    ``drain()`` awaits everything in flight, for tests and scripts that want
    to observe the end state of a chain.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = {}
        self._tasks: set[asyncio.Task] = set()

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._handlers.setdefault(topic, []).append(handler)

    async def publish(self, topic: str, message: Message) -> None:
        for handler in self._handlers.get(topic, []):
            task = asyncio.create_task(self._run(topic, handler, message))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _run(self, topic: str, handler: Handler, message: Message) -> None:
        try:
            await handler(message)
        except Exception:
            logger.exception("stage on %s failed for %s", topic, message)

    async def drain(self) -> None:
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)


class PubSubBus:
    """Publish side only. Delivery is Pub/Sub push → ``api/pubsub.py`` → the
    handler registered here under the topic name."""

    def __init__(self, project: str | None = None, client: Any = None):
        from google.cloud import pubsub_v1

        self._project = project or settings.gcp_project
        self._client = client or pubsub_v1.PublisherClient()
        self._handlers: dict[str, list[Handler]] = {}

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._handlers.setdefault(topic, []).append(handler)

    def handlers(self, topic: str) -> list[Handler]:
        return list(self._handlers.get(topic, []))

    async def publish(self, topic: str, message: Message) -> None:
        path = self._client.topic_path(self._project, topic)
        data = json.dumps(message).encode()
        future = self._client.publish(path, data)
        await asyncio.to_thread(future.result, 30)

    async def deliver(self, topic: str, message: Message) -> None:
        """Called by the push endpoint. Runs every handler inline so a failure
        surfaces as a non-2xx and Pub/Sub retries, then dead-letters."""
        for handler in self._handlers.get(topic, []):
            await handler(message)


#: Topic names as the code refers to them; config maps them to real names.
TOPICS = {
    "media.new": settings.topic_media_new,
    "media.ingested": settings.topic_media_ingested,
    "media.analyzed": settings.topic_media_analyzed,
    "quest.closed": settings.topic_quest_closed,
}
