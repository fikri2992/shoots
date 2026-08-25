"""The real HTTP to blob to Ingest path for Android Phone Source media."""

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import ShotSource, ShotStatus, User
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
    await repo.put_user(ctx.store, User(id="phone-user", email="phone@example.com"))
    ctx.bus.subscribe(TOPICS["media.new"], lambda message: ingest.ingest(ctx, message))
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {
        "id": "phone-user",
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
                    "phone-user",
                    "downstream",
                    "resumed",
                    {},
                    shot_id=message["shot_id"],
                )

            ctx.bus.subscribe(TOPICS["media.ingested"], record_resume)
            third = client.post("/api/ingress/shots", **request)
            await ctx.bus.drain()
    finally:
        main.app.dependency_overrides.clear()

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["created"] is True
    assert second.json() == {**first.json(), "created": False}
    assert third.json() == {**first.json(), "created": False}

    shots = await repo.list_shots(ctx.store, "phone-user")
    assert len(shots) == 1
    shot = shots[0]
    assert shot.source is ShotSource.ANDROID
    assert shot.source_id == request["data"]["source_id"]
    assert shot.drive_file_id == ""
    assert shot.status is ShotStatus.INGESTED
    assert await ctx.blobs.exists(shot.blobs[ORIGINAL])

    stages = [event.stage for event in await repo.list_events(ctx.store, "phone-user")]
    assert stages.count("queued") == 1
    assert stages.count("ingested") == 1
    assert stages.count("resumed") == 1
