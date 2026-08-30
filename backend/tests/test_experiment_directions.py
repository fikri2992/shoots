"""Saved Experiment Direction acceptance through the authenticated API and real Store."""

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    Analysis,
    GridSpec,
    Shot,
    ShotKind,
    ShotStatus,
    TechniqueEvidence,
    TechniqueState,
    TechniqueStatus,
    User,
    now,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.store import InMemoryStore
from app.services.context import Context


async def test_keeper_updates_taste_evidence_without_silently_creating_an_experiment():
    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    user = User(id="keeper_signal_user", email="keeper-signal@example.test")
    shot = Shot(
        id="keeper_signal_source",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        filename="ridge.jpg",
        mime_type="image/jpeg",
        status=ShotStatus.ANALYZED,
        grid=GridSpec(cols=8, rows=6, width=800, height=600),
    )
    await repo.put_user(ctx.store, user)
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="leading_lines",
                    confidence=0.93,
                    agreement=2,
                )
            ],
        ),
    )
    deps.wire(ctx)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            kept = client.put(f"/api/shots/{shot.id}/keeper", json={"keeper": True})
        await ctx.bus.drain()
    finally:
        main.app.dependency_overrides.clear()

    assert kept.status_code == 200, kept.text
    assert kept.json()["kept_at"] is not None
    assert await repo.open_experiment(ctx.store, user.id) is None
    states = {
        state.technique_id: state
        for state in await repo.list_technique_states(ctx.store, user.id)
    }
    assert states["leading_lines"].positive_keeper_shots == 1
    events = await repo.list_events(ctx.store, user.id)
    assert not any(event.agent == "scout" and event.stage == "issued" for event in events)


async def test_save_and_leave_direction_never_create_an_experiment():
    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    user = User(id="direction_user", email="direction@example.test")
    shot = Shot(
        id="direction_source",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        filename="market.jpg",
        mime_type="image/jpeg",
        status=ShotStatus.ANALYZED,
        kept_at=now(),
        grid=GridSpec(cols=8, rows=6, width=800, height=600),
    )
    await repo.put_user(ctx.store, user)
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="leading_lines",
                    confidence=0.93,
                    agreement=2,
                )
            ],
        ),
    )
    await repo.put_technique_state(
        ctx.store,
        TechniqueState(
            user_id=user.id,
            technique_id="leading_lines",
            status=TechniqueStatus.RECURRING,
            attempts=6,
            corroborated=6,
            sightings=6,
            corroborated_shots=6,
            distinct_shoots=3,
            positive_keeper_shots=1,
            shot_ids=[shot.id],
        ),
    )

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            payload = {
                "source_shot_id": shot.id,
                "technique_id": "leading_lines",
                "state": "saved",
            }
            saved = client.put("/api/experiment-directions", json=payload)
            repeated = client.put("/api/experiment-directions", json=payload)
            snapshot = client.get("/api/mobile/snapshot")
            left = client.put(
                "/api/experiment-directions",
                json={**payload, "state": "left"},
            )
            after = client.get("/api/mobile/snapshot")
    finally:
        main.app.dependency_overrides.clear()

    assert saved.status_code == 200, saved.text
    assert repeated.status_code == 200, repeated.text
    assert repeated.json() == saved.json()
    assert saved.json()["state"] == "saved"
    assert saved.json()["warrant_shot_ids"] == [shot.id]
    assert saved.json()["reference_shot_id"] == shot.id
    assert snapshot.json()["experiment_directions"][0]["id"] == saved.json()["id"]
    assert snapshot.json()["open_experiment"] is None
    assert left.status_code == 200, left.text
    assert left.json()["state"] == "left"
    assert after.json()["experiment_directions"][0]["state"] == "left"
    assert await repo.open_experiment(ctx.store, user.id) is None
    events = await repo.list_events(ctx.store, user.id)
    assert sum(event.stage == "experiment_direction_saved" for event in events) == 1
    assert sum(event.stage == "experiment_direction_left" for event in events) == 1
