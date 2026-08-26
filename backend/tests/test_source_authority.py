"""Mine/Inspiration authority through real HTTP, Store, blob, and projection seams."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    Analysis,
    Criteria,
    Experiment,
    ExperimentType,
    JourneyUpdate,
    Provenance,
    Shot,
    ShotKind,
    ShotSource,
    ShotStatus,
    TechniqueEvidence,
    User,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import ORIGINAL, LocalBlobStore, blob_path
from app.infra.store import InMemoryStore
from app.services import cartographer
from app.services.context import Context
from tests.fixtures import jpeg_with_exif


def authority_context(tmp_path) -> Context:
    return Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )


def client_for(ctx: Context, user_id: str) -> TestClient:
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    return TestClient(main.app)


async def test_explicit_inspiration_ingress_never_creates_photographer_work(tmp_path):
    ctx = authority_context(tmp_path)
    user_id = "authority_user"
    await repo.put_user(ctx.store, User(id=user_id, email="authority@example.test"))
    request = {
        "files": {"file": ("reference.jpg", jpeg_with_exif(), "image/jpeg")},
        "data": {
            "source_id": "device:selected:reference",
            "source_role": "inspiration",
        },
    }
    try:
        with client_for(ctx, user_id) as client:
            first = client.post("/api/ingress/shots", **request)
            second = client.post("/api/ingress/shots", **request)
            listed = client.get("/api/inspirations")
            snapshot = client.get("/api/mobile/snapshot")
    finally:
        main.app.dependency_overrides.clear()

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["source_role"] == "inspiration"
    assert first.json()["shot_id"] == ""
    assert first.json()["inspiration_id"]
    assert second.json() == {**first.json(), "created": False}
    assert await repo.list_shots(ctx.store, user_id) == []
    assert await repo.list_runs(ctx.store, user_id) == []
    assert await repo.list_shoots(ctx.store, user_id) == []
    inspirations = await repo.list_inspirations(ctx.store, user_id)
    assert [item.id for item in inspirations] == [first.json()["inspiration_id"]]
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["filename"] == "reference.jpg"
    assert snapshot.status_code == 200, snapshot.text
    assert snapshot.json()["recent_shots"] == []
    assert snapshot.json()["recent_inspirations"][0]["id"] == first.json()["inspiration_id"]
    assert await ctx.blobs.exists(inspirations[0].blobs[ORIGINAL])
    source_signals = await repo.list_photographer_signals(ctx.store, user_id)
    assert [(signal.scope.value, signal.value) for signal in source_signals] == [
        ("inspiration", "inspiration")
    ]
    events = await repo.list_events(ctx.store, user_id)
    assert [event.stage for event in events].count("inspiration_accepted") == 1


async def test_free_manual_shot_correction_rebuilds_memory_and_can_be_restored(tmp_path):
    ctx = authority_context(tmp_path)
    user_id = "authority_user"
    await repo.put_user(ctx.store, User(id=user_id, email="authority@example.test"))
    shot = Shot(
        id="manual_shot",
        user_id=user_id,
        kind=ShotKind.PHOTO,
        source=ShotSource.ANDROID,
        source_id="device:selected:mine",
        filename="mine.jpg",
        mime_type="image/jpeg",
        status=ShotStatus.ANALYZED,
        blobs={ORIGINAL: blob_path(user_id, "manual_shot", ORIGINAL, ".jpg")},
        analyzed_at=datetime(2026, 8, 27, 14, 0, tzinfo=UTC),
    )
    await ctx.blobs.write(shot.blobs[ORIGINAL], jpeg_with_exif(), "image/jpeg")
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=user_id,
            model="reader-v1",
            techniques=[
                TechniqueEvidence(technique_id="panning", confidence=0.9, agreement=2)
            ],
        ),
    )
    assert (await cartographer.rebuild(ctx, user_id))["panning"].sightings == 1
    await repo.put_journey_update(
        ctx.store,
        JourneyUpdate(
            id="journey_from_manual_shot",
            user_id=user_id,
            body="This earlier conclusion cited the manual Shot.",
            provenance=Provenance(shot_ids=[shot.id], sample_size=1),
        ),
    )

    try:
        with client_for(ctx, user_id) as client:
            moved = client.put(
                f"/api/shots/{shot.id}/source-role",
                json={"source_role": "inspiration"},
            )
            shot_list = client.get("/api/shots")
            hidden_detail = client.get(f"/api/shots/{shot.id}")
            retracted = {
                state.technique_id: state
                for state in await repo.list_technique_states(ctx.store, user_id)
            }
            current_journey = client.get("/api/journey")
            inspiration_id = moved.json()["inspiration_id"]
            restored = client.put(
                f"/api/inspirations/{inspiration_id}/source-role",
                json={"source_role": "mine"},
            )
            restored_list = client.get("/api/shots")
    finally:
        main.app.dependency_overrides.clear()

    assert moved.status_code == 200, moved.text
    assert moved.json()["source_role"] == "inspiration"
    assert shot_list.json() == []
    assert hidden_detail.status_code == 404
    assert retracted["panning"].sightings == 0
    assert current_journey.json() == []
    historical_journey = await repo.list_journey_updates(
        ctx.store,
        user_id,
        include_superseded=True,
    )
    assert historical_journey[0].superseded_reason == (
        "A cited Shot was corrected to Inspiration."
    )
    assert restored.status_code == 200, restored.text
    assert restored.json() == {
        "source_role": "mine",
        "shot_id": shot.id,
        "inspiration_id": "",
    }
    assert restored_list.json()[0]["shot"]["id"] == shot.id
    current = {
        state.technique_id: state
        for state in await repo.list_technique_states(ctx.store, user_id)
    }
    assert current["panning"].sightings == 1
    assert await repo.list_inspirations(ctx.store, user_id) == []
    current_source = await repo.list_photographer_signals(ctx.store, user_id)
    assert [(signal.scope.value, signal.value) for signal in current_source] == [
        ("shot", "mine")
    ]
    source_history = await repo.list_photographer_signals(
        ctx.store,
        user_id,
        include_superseded=True,
    )
    assert len(source_history) == 2


async def test_experiment_cited_shot_refuses_source_role_reclassification(tmp_path):
    ctx = authority_context(tmp_path)
    user_id = "authority_user"
    await repo.put_user(ctx.store, User(id=user_id, email="authority@example.test"))
    shot = Shot(
        id="reference_shot",
        user_id=user_id,
        kind=ShotKind.PHOTO,
        source=ShotSource.ANDROID,
        source_id="device:selected:reference",
        filename="reference.jpg",
        mime_type="image/jpeg",
    )
    await repo.put_shot(ctx.store, shot)
    await repo.put_experiment(
        ctx.store,
        Experiment(
            id="reproduce",
            user_id=user_id,
            technique_id="panning",
            type=ExperimentType.REPRODUCE,
            title="Repeat panning",
            brief="Repeat the motion.",
            why_now="Keeper evidence",
            criteria=Criteria(vision=["panning"]),
            reference_shot_id=shot.id,
        ),
    )
    try:
        with client_for(ctx, user_id) as client:
            response = client.put(
                f"/api/shots/{shot.id}/source-role",
                json={"source_role": "inspiration"},
            )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "Experiment" in response.json()["detail"]
    assert (await repo.list_shots(ctx.store, user_id))[0].id == shot.id
    assert await repo.list_inspirations(ctx.store, user_id) == []
