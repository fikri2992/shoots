"""Explicit Drive selection through real HTTP, stores, blobs, bus, and local Drive."""

import httpx

from app.api import deps, main
from app.api.auth import current_user
from app.config import settings
from app.domain.entities import ShotSource, ShotStatus, SourceRole, User
from app.infra import repository as repo
from app.infra.bus import TOPICS, InProcessBus
from app.infra.drive import LocalDriveClient
from app.infra.storage import ORIGINAL, LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import ingest
from app.services.context import Context
from tests.fixtures import jpeg_with_exif


async def test_selected_drive_files_enter_mine_or_inspiration_once(tmp_path, monkeypatch):
    drive_root = tmp_path / "drive"
    drive_root.mkdir()
    (drive_root / "mine.jpg").write_bytes(jpeg_with_exif(width=640, height=480))
    (drive_root / "reference.jpg").write_bytes(jpeg_with_exif(width=480, height=640))
    drive = LocalDriveClient(drive_root)
    files = {item.name: item for item in await drive.list_media("local")}
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=drive,
        tokens=None,
    )
    user_id = "dev:picker@example.test"
    await repo.put_user(ctx.store, User(id=user_id, email="picker@example.test"))
    ctx.bus.subscribe(TOPICS["media.new"], lambda message: ingest.ingest(ctx, message))
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    monkeypatch.setattr(settings, "drive_local_folder", str(drive_root))

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app),
            base_url="http://test",
        ) as client:
            mine = await client.post(
                "/drive/import",
                json={
                    "file_ids": [files["mine.jpg"].id, files["mine.jpg"].id],
                    "source_role": "mine",
                },
            )
            await ctx.bus.drain()
            duplicate = await client.post(
                "/drive/import",
                json={"file_ids": [files["mine.jpg"].id], "source_role": "mine"},
            )
            inspiration = await client.post(
                "/drive/import",
                json={
                    "file_ids": [files["reference.jpg"].id],
                    "source_role": "inspiration",
                },
            )
    finally:
        main.app.dependency_overrides.clear()

    assert mine.status_code == 200, mine.text
    assert mine.json()["discovered"] == 1
    assert mine.json()["imported"] == 1
    assert duplicate.json()["duplicates"] == 1
    assert inspiration.status_code == 200, inspiration.text
    assert inspiration.json()["imported"] == 1

    shots = await repo.list_shots(ctx.store, user_id)
    assert len(shots) == 1
    assert shots[0].source is ShotSource.DRIVE_PICKER
    assert shots[0].status is ShotStatus.INGESTED
    assert await ctx.blobs.exists(shots[0].blobs[ORIGINAL])
    inspirations = await repo.list_inspirations(ctx.store, user_id)
    assert len(inspirations) == 1
    assert inspirations[0].source is ShotSource.DRIVE_PICKER
    assert await ctx.blobs.exists(inspirations[0].blobs[ORIGINAL])

    signals = await repo.list_photographer_signals(ctx.store, user_id)
    roles = {(signal.scope.value, signal.value) for signal in signals}
    assert ("shot", SourceRole.MINE.value) in roles
    assert ("inspiration", SourceRole.INSPIRATION.value) in roles

    user = await repo.get_user(ctx.store, user_id)
    user.drive_folder_id = "local"
    await repo.put_user(ctx.store, user)
    assert await ingest.sync(ctx, user) == []


async def test_browser_upload_has_distinct_provenance(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "dev:web@example.test"
    await repo.put_user(ctx.store, User(id=user_id, email="web@example.test"))
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/ingress/shots",
                files={"file": ("browser.jpg", jpeg_with_exif(), "image/jpeg")},
                data={"source_id": "web:browser.jpg:1", "source_role": "mine"},
            )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    shot = await repo.get_shot(ctx.store, response.json()["shot_id"])
    assert shot.source is ShotSource.WEB_UPLOAD
