"""Contract tests: the in-memory store, typed repository, token store and bus.

Firestore runs the same store tests when FIRESTORE_EMULATOR_HOST is set.
"""

import asyncio
import os

import pytest

from app.domain.entities import Criteria, Quest, QuestStatus, Shot, ShotKind, SkillState, User
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.secrets import LocalTokenStore
from app.infra.store import InMemoryStore


def stores():
    yield "memory", InMemoryStore
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        from app.infra.store import FirestoreStore

        yield "firestore", FirestoreStore


@pytest.fixture(params=list(stores()), ids=lambda p: p[0])
def store(request):
    return request.param[1]()


async def test_put_get_query_order_limit(store):
    for i in range(3):
        await store.put("t", f"d{i}", {"n": i, "user_id": "u", "tag_ids": ["a", f"t{i}"]})
    assert (await store.get("t", "d1"))["n"] == 1
    assert await store.get("t", "missing") is None
    rows = await store.query("t", where={"user_id": "u"}, order_by="n", descending=True, limit=2)
    assert [r["n"] for r in rows] == [2, 1]
    assert len(await store.query("t", where={"tag_ids": "t0"})) == 1
    await store.delete("t", "d0")
    assert await store.get("t", "d0") is None


async def test_repository_round_trips_every_entity(store):
    user = User(id="u1", email="a@b.c", drive_folder_id="f")
    await repo.put_user(store, user)
    assert (await repo.get_user(store, "u1")).drive_folder_id == "f"
    assert await repo.find_user(store, "nope") is None
    with pytest.raises(repo.UnknownEntity):
        await repo.get_user(store, "nope")

    shot = Shot(
        id=repo.shot_id_for("u1", "file1"),
        user_id="u1",
        kind=ShotKind.PHOTO,
        drive_file_id="file1",
        filename="a.jpg",
        mime_type="image/jpeg",
    )
    await repo.put_shot(store, shot)
    assert [s.id for s in await repo.list_shots(store, "u1")] == [shot.id]

    skill = SkillState(user_id="u1", technique_id="panning", attempts=2)
    await repo.put_skill(store, skill)
    assert (await repo.list_skills(store, "u1"))[0].attempts == 2

    quest = Quest(
        id="q1",
        user_id="u1",
        technique_id="panning",
        title="t",
        brief="b",
        why_now="w",
        criteria=Criteria(),
    )
    await repo.put_quest(store, quest)
    assert (await repo.open_quest(store, "u1")).id == "q1"
    quest.status = QuestStatus.PASSED
    await repo.put_quest(store, quest)
    assert await repo.open_quest(store, "u1") is None

    await repo.record(store, "u1", "ingest", "queued", {"x": 1}, shot_id=shot.id)
    events = await repo.list_events(store, "u1")
    assert events[0].stage == "queued" and events[0].shot_id == shot.id


def test_shot_id_is_deterministic():
    assert repo.shot_id_for("u", "f") == repo.shot_id_for("u", "f")
    assert repo.shot_id_for("u", "f") != repo.shot_id_for("u", "g")


async def test_local_token_store_round_trip(tmp_path):
    tokens = LocalTokenStore(tmp_path)
    assert await tokens.get("user:1") is None
    await tokens.put("user:1", {"refresh_token": "r"})
    assert (await tokens.get("user:1"))["refresh_token"] == "r"
    await tokens.delete("user:1")
    assert await tokens.get("user:1") is None


async def test_in_process_bus_runs_handlers_and_isolates_failures():
    bus = InProcessBus()
    seen = []

    async def good(message):
        await asyncio.sleep(0.01)
        seen.append(message["n"])

    async def bad(message):
        raise RuntimeError("boom")

    bus.subscribe("t", bad)
    bus.subscribe("t", good)
    await bus.publish("t", {"n": 1})
    await bus.publish("t", {"n": 2})
    await bus.drain()
    assert sorted(seen) == [1, 2]
