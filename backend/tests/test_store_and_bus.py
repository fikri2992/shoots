"""Contract tests: the in-memory store, typed repository, token store and bus.

Firestore runs the same store tests when FIRESTORE_EMULATOR_HOST is set.
"""

import asyncio
import os
import uuid

import pytest

from app.domain.entities import (
    Analysis,
    Composition,
    Criteria,
    Experiment,
    ExperimentStatus,
    Shot,
    ShotKind,
    TechniqueState,
    TechniqueStatus,
    User,
    Verdict,
    now,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.secrets import LocalTokenStore
from app.infra.store import FileStore, InMemoryStore
from app.services import profile as profile_service
from app.services.context import Context


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
    assert await store.create("t", "unique", {"owner": "u1"}) is True
    assert await store.create("t", "unique", {"owner": "u2"}) is False
    assert await store.delete_if("t", "unique", {"owner": "u2"}) is False
    assert await store.patch_if("t", "unique", {"value": 3}, {"owner": "u2"}) is False
    assert await store.patch_if("t", "unique", {"value": 3}, {"owner": "u1"}) is True
    assert (await store.get("t", "unique"))["value"] == 3
    assert await store.delete_if("t", "unique", {"owner": "u1"}) is True
    assert await store.create_claimed(
        "claims", "owner", {"document_id": "paired"}, "t", "paired", {"value": 1}
    )
    assert await store.get("claims", "owner") == {"document_id": "paired"}
    assert await store.get("t", "paired") == {"value": 1}
    assert not await store.create_claimed(
        "claims", "owner", {"document_id": "other"}, "t", "other", {"value": 2}
    )
    assert await store.get("t", "other") is None
    await store.put("counter", "one", {"value": 0})

    def increment(document):
        document["value"] += 1
        return document

    await asyncio.gather(*(store.mutate("counter", "one", increment) for _ in range(8)))
    assert (await store.get("counter", "one"))["value"] == 8
    unchanged, changed = await store.mutate("counter", "one", lambda document: None)
    assert changed is False and unchanged["value"] == 8


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

    state = TechniqueState(user_id="u1", technique_id="panning", attempts=2)
    await repo.put_technique_state(store, state)
    assert (await repo.list_technique_states(store, "u1"))[0].attempts == 2

    # A migrated graded label cannot outrank the Evidence counts. Repository
    # contracts protect every service and API surface, not only this UI.
    impossible = TechniqueState(
        user_id="u1",
        technique_id="leading_lines",
        status=TechniqueStatus.RECURRING,
        attempts=8,
        corroborated=0,
    )
    await repo.put_technique_state(store, impossible)
    loaded = {item.technique_id: item for item in await repo.list_technique_states(store, "u1")}
    assert loaded["leading_lines"].status is TechniqueStatus.OBSERVED

    experiment = Experiment(
        id="q1",
        user_id="u1",
        technique_id="panning",
        title="t",
        brief="b",
        why_now="w",
        criteria=Criteria(),
    )
    await repo.put_experiment(store, experiment)
    assert (await repo.open_experiment(store, "u1")).id == "q1"
    experiment.status = ExperimentStatus.COMPLETED
    await repo.put_experiment(store, experiment)
    assert await repo.open_experiment(store, "u1") is None

    await repo.record(store, "u1", "ingest", "queued", {"x": 1}, shot_id=shot.id)
    events = await repo.list_events(store, "u1")
    assert events[0].stage == "queued" and events[0].shot_id == shot.id


async def test_concurrent_open_experiment_creation_has_one_winner(store):
    user_id = f"user_atomic_{uuid.uuid4().hex}"

    def candidate(number: int) -> Experiment:
        return Experiment(
            id=f"experiment_atomic_{uuid.uuid4().hex}_{number}",
            user_id=user_id,
            technique_id="panning",
            title=f"candidate {number}",
            brief="Follow one subject.",
            why_now="A cited Tendency supports it.",
            criteria=Criteria(),
        )

    experiments = [candidate(number) for number in range(8)]
    results = await asyncio.gather(
        *(repo.create_open_experiment(store, experiment) for experiment in experiments)
    )

    assert sum(results) == 1
    opened = await repo.open_experiment(store, user_id)
    assert opened is not None
    assert opened.id == experiments[results.index(True)].id
    stored = await repo.list_experiments(store, user_id)
    assert [experiment.id for experiment in stored] == [opened.id]


async def test_skip_and_verdict_cannot_overwrite_each_other(store):
    suffix = uuid.uuid4().hex
    experiment = Experiment(
        id=f"experiment_transition_race_{suffix}",
        user_id=f"user_transition_race_{suffix}",
        technique_id="panning",
        title="race",
        brief="Follow one subject.",
        why_now="A cited Tendency supports it.",
        criteria=Criteria(),
    )
    assert await repo.create_open_experiment(store, experiment)
    verdict = Verdict(
        shot_id="race_shot",
        criteria_met=True,
        feedback="The declared Criteria were met.",
    )

    judged, skipped = await asyncio.gather(
        repo.append_verdict_if_open(store, experiment.id, verdict, now()),
        repo.transition_open_experiment(store, experiment.id, ExperimentStatus.SKIPPED, now()),
    )

    assert sum((judged[1], skipped[1])) == 1
    stored = await repo.get_experiment(store, experiment.id)
    if stored.status is ExperimentStatus.COMPLETED:
        assert [item.shot_id for item in stored.verdicts] == ["race_shot"]
    else:
        assert stored.status is ExperimentStatus.SKIPPED and stored.verdicts == []


async def test_tendency_profile_reads_beyond_the_old_500_shot_window():
    store = InMemoryStore()
    ctx = Context(store=store, blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    for number in range(505):
        shot_id = f"archive_{number}"
        await repo.put_shot(
            store,
            Shot(
                id=shot_id,
                user_id="archive_user",
                kind=ShotKind.PHOTO,
                drive_file_id=shot_id,
                filename=f"{shot_id}.jpg",
                mime_type="image/jpeg",
            ),
        )
        await repo.put_analysis(
            store,
            Analysis(
                shot_id=shot_id,
                user_id="archive_user",
                model="reader-v1",
                prompt_version="prompt-v1",
                composition=Composition(subject_x=0.5, subject_y=0.5),
            ),
        )

    profile = await profile_service.build(ctx, "archive_user")

    assert profile.shots == 505
    assert len(profile.shot_ids) == 505
    assert profile.model_inputs == (("reader-v1", "prompt-v1"),)


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


async def test_file_store_survives_a_restart(tmp_path):
    path = tmp_path / "store.json"
    first = FileStore(path)
    await first.put("users", "u1", {"id": "u1", "drive_folder_id": "f"})
    await first.put("users", "u2", {"id": "u2"})
    await first.delete("users", "u2")

    second = FileStore(path)  # a new process
    assert (await second.get("users", "u1"))["drive_folder_id"] == "f"
    assert await second.get("users", "u2") is None
    assert len(await second.query("users")) == 1
