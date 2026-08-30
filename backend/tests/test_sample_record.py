"""A hand-authored Sample Record stays readable and cannot accept real actions."""

import base64
import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner

from app.api import deps, main
from app.api.auth import SESSION_USER_KEY
from app.config import settings
from app.domain.entities import (
    RecordMode,
    Run,
    RunStatus,
    Shoot,
    ShootStatus,
    Shot,
    ShotKind,
    ShotSource,
    User,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services.context import Context


def _session_cookie(user_id: str) -> str:
    payload = base64.b64encode(
        json.dumps({SESSION_USER_KEY: {"id": user_id, "email": "sample@example.test"}}).encode()
    )
    return TimestampSigner(str(settings.session_secret)).sign(payload).decode()


async def test_sample_record_is_visible_but_read_only_through_the_real_api(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user = User(
        id="sample-user",
        email="sample@example.test",
        record_mode=RecordMode.SAMPLE,
    )
    shot = Shot(
        id="sample-shot",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        filename="sample.jpg",
        mime_type="image/jpeg",
    )
    await repo.put_user(ctx.store, user)
    await repo.put_shot(ctx.store, shot)

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    try:
        with TestClient(main.app) as client:
            client.cookies.set("session", _session_cookie(user.id))
            snapshot = client.get("/api/mobile/snapshot")
            keeper = client.put("/api/shots/sample-shot/keeper", json={"keeper": True})
    finally:
        main.app.dependency_overrides.clear()

    assert snapshot.status_code == 200, snapshot.text
    assert snapshot.json()["user"]["record_mode"] == "sample"
    assert keeper.status_code == 409, keeper.text
    assert keeper.json()["detail"] == "Sample Records are read-only interface fixtures"
    assert (await repo.get_shot(ctx.store, shot.id)).kept_at is None


async def test_scheduled_background_work_skips_sample_records(tmp_path, monkeypatch):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user = User(
        id="sample-user",
        email="sample@example.test",
        record_mode=RecordMode.SAMPLE,
    )
    stale = datetime.now(UTC) - timedelta(hours=2)
    shoot = Shoot(
        id="sample-shoot",
        user_id=user.id,
        status=ShootStatus.OPEN,
        started_at=stale,
        last_capture_at=stale,
    )
    run = Run(
        id="run_sample-shot",
        user_id=user.id,
        shot_id="sample-shot",
        source=ShotSource.WEB_UPLOAD,
        status=RunStatus.RETRYING,
        started_at=stale,
        updated_at=stale,
    )
    await repo.put_user(ctx.store, user)
    await repo.put_shoot(ctx.store, shoot)
    await ctx.store.put(repo.RUNS, run.id, run.model_dump(mode="json"))

    monkeypatch.setattr(settings, "tasks_token", "sample-test-token")
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    try:
        with TestClient(main.app) as client:
            tick = client.post(
                "/tasks/tick",
                headers={"X-Tasks-Token": "sample-test-token"},
            )
    finally:
        main.app.dependency_overrides.clear()

    assert tick.status_code == 200, tick.text
    assert tick.json() == {
        "queued": 0,
        "delivered": 0,
        "capture_sessions_expired": 0,
        "shoots_closed": 0,
        "runs_replayed": 0,
    }
    assert (await repo.get_shoot(ctx.store, shoot.id)).status is ShootStatus.OPEN
    assert (await repo.get_run(ctx.store, run.id)).status is RunStatus.RETRYING
