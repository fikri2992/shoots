"""The real HTTP to blob to Ingest path for Android Phone Source media."""

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.config import settings
from app.domain.entities import RunStatus, ShotSource, ShotStatus, User
from app.infra import repository as repo
from app.infra.bus import TOPICS, InProcessBus
from app.infra.storage import ORIGINAL, LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import ingest
from app.services.context import Context
from tests.fixtures import jpeg_with_exif


async def test_android_ingress_is_idempotent_and_runs_the_real_ingest(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "dev:phone@example.test"
    await repo.put_user(ctx.store, User(id=user_id, email="phone@example.test"))
    ctx.bus.subscribe(TOPICS["media.new"], lambda message: ingest.ingest(ctx, message))
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {
        "id": user_id,
        "device": "Android phone",
    }

    data = jpeg_with_exif()
    request = {
        "files": {"file": ("IMG_20260826.jpg", data, "image/jpeg")},
        "data": {"source_id": "external_primary:812:1787712000:18423"},
    }
    try:
        with TestClient(main.app) as client:
            first = client.post("/api/ingress/shots", **request)
            second = client.post("/api/ingress/shots", **request)
            await ctx.bus.drain()

            async def record_resume(message: dict) -> None:
                await repo.record(
                    ctx.store,
                    user_id,
                    "downstream",
                    "resumed",
                    {},
                    shot_id=message["shot_id"],
                )

            ctx.bus.subscribe(TOPICS["media.ingested"], record_resume)
            third = client.post("/api/ingress/shots", **request)
            await ctx.bus.drain()
            stored = (await repo.list_shots(ctx.store, user_id))[0]
            blob_response = client.get(f"/api/blobs/{stored.blobs[ORIGINAL]}")
    finally:
        main.app.dependency_overrides.clear()

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["created"] is True
    assert second.json() == {**first.json(), "created": False}
    assert third.json() == {**first.json(), "created": False}

    shots = await repo.list_shots(ctx.store, user_id)
    assert len(shots) == 1
    shot = shots[0]
    assert shot.source is ShotSource.ANDROID
    assert shot.source_id == request["data"]["source_id"]
    assert shot.drive_file_id == ""
    assert shot.status is ShotStatus.INGESTED
    assert await ctx.blobs.exists(shot.blobs[ORIGINAL])
    assert blob_response.status_code == 200
    assert blob_response.headers["content-type"] == "image/jpeg"

    run = await repo.find_run_for_shot(ctx.store, shot.id)
    assert run is not None
    assert run.status is RunStatus.RUNNING

    stages = [event.stage for event in await repo.list_events(ctx.store, user_id)]
    assert stages.count("queued") == 1
    assert stages.count("ingested") == 1
    assert stages.count("resumed") == 1


async def test_android_ingress_accepts_exact_limit_and_rejects_one_byte_over(tmp_path, monkeypatch):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "dev:limit@example.test"
    await repo.put_user(ctx.store, User(id=user_id, email="limit@example.test"))
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id, "device": "Android"}
    data = jpeg_with_exif(width=120, height=80)
    monkeypatch.setattr(settings, "max_upload_bytes", len(data))
    try:
        with TestClient(main.app) as client:
            exact = client.post(
                "/api/ingress/shots",
                files={"file": ("exact.jpg", data, "image/jpeg")},
                data={"source_id": "limit:exact"},
            )
            over = client.post(
                "/api/ingress/shots",
                files={"file": ("over.jpg", data + b"x", "image/jpeg")},
                data={"source_id": "limit:over"},
            )
    finally:
        main.app.dependency_overrides.clear()

    assert exact.status_code == 200, exact.text
    assert over.status_code == 413, over.text
    stored = await repo.get_shot(ctx.store, exact.json()["shot_id"])
    assert await ctx.blobs.read(stored.blobs[ORIGINAL]) == data
