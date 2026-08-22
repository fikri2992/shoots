"""Drive channel lifecycle rules and Pub/Sub push decoding and per-stage delivery."""

import base64
import json
import tempfile
from datetime import UTC, datetime, timedelta

import pytest

from app.api import pubsub
from app.domain.entities import DriveChannel, User
from app.infra import repository as repo
from app.infra.bus import InProcessBus, PubSubBus
from app.infra.drive import LocalDriveClient
from app.infra.secrets import LocalTokenStore
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import watch
from app.services.context import Context


def test_renewal_rule():
    at = datetime(2026, 8, 23, 12, tzinfo=UTC)
    assert watch.needs_renewal(None, at)
    fresh = DriveChannel(channel_id="c", resource_id="r", expires_at=at + timedelta(hours=20))
    assert not watch.needs_renewal(fresh, at)
    soon = DriveChannel(channel_id="c", resource_id="r", expires_at=at + timedelta(hours=2))
    assert watch.needs_renewal(soon, at)


async def test_local_dev_opens_no_channel(monkeypatch):
    monkeypatch.setattr(watch.settings, "drive_webhook_url", "http://localhost:8000/drive/notify")
    with tempfile.TemporaryDirectory() as folder:
        ctx = Context(
            store=InMemoryStore(),
            blobs=LocalBlobStore(folder),
            bus=InProcessBus(),
            drive=LocalDriveClient(folder),
            tokens=LocalTokenStore(folder),
        )
        user = User(id="u1", email="u@x", drive_folder_id="local")
        await repo.put_user(ctx.store, user)
        assert await watch.ensure(ctx, user) is None
        assert await watch.renew_all(ctx) == 0
        assert (await repo.get_user(ctx.store, "u1")).drive_channel is None


def envelope(payload) -> pubsub.PushEnvelope:
    data = base64.b64encode(json.dumps(payload).encode()).decode()
    return pubsub.PushEnvelope(message=pubsub.PushMessage(data=data, messageId="1"))


def test_decode_push_envelope():
    assert pubsub.decode(envelope({"shot_id": "s1"})) == {"shot_id": "s1"}
    assert pubsub.decode(pubsub.PushEnvelope(message=pubsub.PushMessage())) == {}
    with pytest.raises(ValueError):
        pubsub.decode(envelope([1, 2]))


class RecordingPublisher:
    """Just enough of the publisher client for the publish path."""

    def __init__(self):
        self.published = []

    def topic_path(self, project, topic):
        return f"projects/{project}/topics/{topic}"

    def publish(self, path, data):
        self.published.append((path, json.loads(data)))

        class Done:
            def result(self, timeout=None):
                return "id"

        return Done()


async def test_pubsub_bus_delivers_one_stage_at_a_time():
    bus = PubSubBus(project="p", client=RecordingPublisher())
    ran = []

    async def cartographer(message):
        ran.append(("cartographer", message["shot_id"]))

    async def judge(message):
        ran.append(("judge", message["shot_id"]))

    bus.subscribe("shoots.media.analyzed", cartographer, stage="cartographer")
    bus.subscribe("shoots.media.analyzed", judge, stage="judge")
    assert sorted(bus.stages()) == ["cartographer", "judge"]

    await bus.deliver("judge", {"shot_id": "s1"})
    assert ran == [("judge", "s1")]

    await bus.publish("shoots.media.analyzed", {"shot_id": "s2"})
    assert bus._client.published == [("projects/p/topics/shoots.media.analyzed", {"shot_id": "s2"})]

    with pytest.raises(KeyError):
        await bus.deliver("nope", {})


def test_verify_rejects_missing_token():
    with pytest.raises(Exception) as caught:
        pubsub.verify(None)
    assert caught.value.status_code == 401
