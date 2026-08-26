"""Android read models stay cacheable and page without breaking web."""

from datetime import timedelta

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import Shot, ShotKind, User, now
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services.context import Context


async def test_mobile_snapshot_etag_and_compatible_shot_cursor(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "mobile-reader"
    await repo.put_user(ctx.store, User(id=user_id, email="reader@example.test"))
    at = now()
    for index in range(4):
        offset = 2 if index >= 2 else index
        await repo.put_shot(
            ctx.store,
            Shot(
                id=f"shot-{index}",
                user_id=user_id,
                kind=ShotKind.PHOTO,
                filename=f"IMG_{index}.jpg",
                mime_type="image/jpeg",
                ingested_at=at + timedelta(seconds=offset),
            ),
        )

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            first = client.get("/api/shots?limit=2")
            assert first.status_code == 200, first.text
            assert isinstance(first.json(), list)
            assert [row["shot"]["id"] for row in first.json()] == ["shot-3", "shot-2"]
            cursor = first.headers["X-Next-Cursor"]

            second = client.get("/api/shots", params={"limit": 2, "cursor": cursor})
            assert second.status_code == 200, second.text
            assert [row["shot"]["id"] for row in second.json()] == ["shot-1", "shot-0"]
            assert "X-Next-Cursor" not in second.headers

            snapshot = client.get("/api/mobile/snapshot")
            assert snapshot.status_code == 200, snapshot.text
            etag = snapshot.headers["ETag"]
            unchanged = client.get("/api/mobile/snapshot", headers={"If-None-Match": etag})
            assert unchanged.status_code == 304
            assert unchanged.content == b""
    finally:
        main.app.dependency_overrides.clear()
