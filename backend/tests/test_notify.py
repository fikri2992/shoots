"""Subscription bookkeeping on a real store; delivery is external and is
checked with /api/push/test on a device."""

import pytest

from app.infra.store import InMemoryStore
from app.services import notify


async def test_subscribe_is_per_device_and_idempotent():
    store = InMemoryStore()
    sub = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "k", "auth": "a"}}
    first = await notify.subscribe(store, "u1", sub)
    second = await notify.subscribe(store, "u1", sub)
    assert first == second
    other = await notify.subscribe(
        store, "u1", {"endpoint": "https://push.example/xyz", "keys": {"p256dh": "k", "auth": "a"}}
    )
    assert other != first
    assert len(await notify.list_subscriptions(store, "u1")) == 2
    assert await notify.list_subscriptions(store, "u2") == []

    await notify.unsubscribe(store, "u1", "https://push.example/abc")
    assert [r["id"] for r in await notify.list_subscriptions(store, "u1")] == [other]


async def test_subscribe_rejects_garbage():
    store = InMemoryStore()
    with pytest.raises(ValueError):
        await notify.subscribe(store, "u1", {"endpoint": ""})
    with pytest.raises(ValueError):
        await notify.subscribe(store, "u1", {"endpoint": "https://x", "nokeys": 1})
