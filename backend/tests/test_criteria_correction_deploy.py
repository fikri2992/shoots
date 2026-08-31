"""Retired Criteria correction: real HTTP guards, replay and atomic store contracts.

Candidates below are stored test data, not assertions about Scout model quality.
The real Scout acceptance script covers generation separately.
"""

import asyncio
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain import experiment_criteria, taxonomy
from app.domain.entities import (
    Criteria,
    ExifRule,
    Experiment,
    ExperimentStatus,
    ExperimentType,
    User,
    Verdict,
    now,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import LocalBlobStore
from app.infra.store import FileStore, InMemoryStore
from app.services.context import Context


@pytest.fixture(params=["memory", "file", "firestore"])
def store(request, tmp_path):
    if request.param == "file":
        return FileStore(tmp_path / "store.json")
    if request.param == "firestore":
        if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
            pytest.skip("Firestore emulator is not configured; production transaction unexecuted")
        from app.infra.store import FirestoreStore

        return FirestoreStore()
    return InMemoryStore()


def experiments(user_id: str) -> tuple[Experiment, Experiment]:
    previous = Experiment(
        id=f"legacy_{uuid.uuid4().hex}",
        user_id=user_id,
        technique_id="deep_dof",
        type=ExperimentType.REPRODUCE,
        title="Near and far",
        brief="Use f/8.",
        why_now="A stored Keeper supported this visual goal.",
        criteria=Criteria(exif=ExifRule(aperture_min=8.0), vision=["deep_dof"]),
        verdicts=[Verdict(shot_id="historical", criteria_met=False, feedback="Original feedback")],
        result_shot_ids=["historical"],
    )
    replacement = Experiment(
        id=repo.corrected_experiment_id(user_id, previous.id),
        user_id=user_id,
        technique_id="deep_dof",
        type=ExperimentType.REPRODUCE,
        title="Near and far with a visual check",
        brief="Keep nearby and distant detail visibly sharp.",
        why_now="The same visual goal, without an aperture proxy.",
        criteria=experiment_criteria.for_technique(taxonomy.BY_ID["deep_dof"], []),
    )
    return previous, replacement


async def test_correction_atomic_swap_retains_history_and_one_winner(store):
    user_id = f"correction_{uuid.uuid4().hex}"
    previous, replacement = experiments(user_id)
    assert await repo.create_open_experiment(store, previous)
    results = await asyncio.gather(
        *(repo.replace_legacy_experiment(store, previous, replacement) for _ in range(8))
    )
    assert sum(results) == 1
    old = await repo.get_experiment(store, previous.id)
    assert old.status is ExperimentStatus.LEFT
    assert old.closed_at is not None
    assert old.criteria == previous.criteria
    assert old.verdicts == previous.verdicts
    assert old.result_shot_ids == previous.result_shot_ids
    assert (await repo.open_experiment(store, user_id)).id == replacement.id
    assert {item.id for item in await repo.list_experiments(store, user_id)} == {
        previous.id,
        replacement.id,
    }
    if isinstance(store, FileStore):
        restarted = FileStore(store.path)
        assert (await repo.open_experiment(restarted, user_id)).id == replacement.id
        assert (await repo.get_experiment(restarted, previous.id)) == old


@pytest.mark.parametrize("interference", ["focus_changed", "previous_closed", "new_id_exists"])
async def test_correction_atomic_refusal_never_partially_writes(store, interference):
    user_id = f"correction_{uuid.uuid4().hex}"
    previous, replacement = experiments(user_id)
    assert await repo.create_open_experiment(store, previous)
    if interference == "focus_changed":
        await store.put(
            repo.OPEN_EXPERIMENTS,
            user_id,
            {"user_id": user_id, "experiment_id": "another-open-focus"},
        )
    elif interference == "previous_closed":
        await repo.transition_open_experiment(store, previous.id, ExperimentStatus.COMPLETED, now())
    else:
        await store.put(repo.EXPERIMENTS, replacement.id, replacement.model_dump(mode="json"))
    before = (
        await store.get(repo.OPEN_EXPERIMENTS, user_id),
        await store.get(repo.EXPERIMENTS, previous.id),
        await store.get(repo.EXPERIMENTS, replacement.id),
    )
    assert not await repo.replace_legacy_experiment(store, previous, replacement)
    assert before == (
        await store.get(repo.OPEN_EXPERIMENTS, user_id),
        await store.get(repo.EXPERIMENTS, previous.id),
        await store.get(repo.EXPERIMENTS, replacement.id),
    )


async def test_correction_http_retry_returns_same_replacement_even_after_completion(tmp_path):
    ctx = Context(
        store=FileStore(tmp_path / "store.json"),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "correction-owner"
    await repo.put_user(ctx.store, User(id=user_id, email="owner@example.test"))
    previous, replacement = experiments(user_id)
    assert await repo.create_open_experiment(ctx.store, previous)
    assert await repo.replace_legacy_experiment(ctx.store, previous, replacement)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            for _ in range(2):
                response = client.post(f"/api/experiments/{previous.id}/correct-criteria")
                assert response.status_code == 200, response.text
                assert response.json()["id"] == replacement.id
                assert response.json()["criteria_notice"] == ""
            await repo.transition_open_experiment(
                ctx.store, replacement.id, ExperimentStatus.COMPLETED, now()
            )
            await repo.release_open_experiment(ctx.store, user_id, replacement.id)
            response = client.post(f"/api/experiments/{previous.id}/correct-criteria")
            assert response.status_code == 200, response.text
            assert response.json()["id"] == replacement.id
            assert response.json()["status"] == "completed"
        assert await repo.open_experiment(ctx.store, user_id) is None
        assert len(await repo.list_experiments(ctx.store, user_id)) == 2
        old = await repo.get_experiment(ctx.store, previous.id)
        assert old.criteria == previous.criteria
        assert old.verdicts == previous.verdicts
        assert old.result_shot_ids == previous.result_shot_ids
    finally:
        main.app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("case", "status"),
    [
        ("missing", 404),
        ("foreign", 404),
        ("supported", 409),
        ("closed", 409),
        ("wrong_focus", 409),
        ("no_keeper", 409),
    ],
)
async def test_correction_http_guards_preserve_records(tmp_path, case, status):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "correction-owner"
    await repo.put_user(ctx.store, User(id=user_id, email="owner@example.test"))
    previous, replacement = experiments("other" if case == "foreign" else user_id)
    if case == "supported":
        previous.criteria = replacement.criteria
    if case == "closed":
        previous.status = ExperimentStatus.COMPLETED
    if case != "missing":
        await repo.put_experiment(ctx.store, previous)
    if case == "wrong_focus":
        other_focus = replacement.model_copy(update={"id": f"other_{uuid.uuid4().hex}"})
        assert await repo.create_open_experiment(ctx.store, other_focus)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    before = await repo.find_experiment(ctx.store, previous.id)
    try:
        with TestClient(main.app) as client:
            response = client.post(f"/api/experiments/{previous.id}/correct-criteria")
            assert response.status_code == status, response.text
        assert (await repo.find_experiment(ctx.store, previous.id)) == before
        if case == "wrong_focus":
            assert (await repo.open_experiment(ctx.store, user_id)).id == other_focus.id
        assert (await repo.find_experiment(ctx.store, replacement.id)) is None
    finally:
        main.app.dependency_overrides.clear()
