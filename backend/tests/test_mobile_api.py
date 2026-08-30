"""Android read models stay cacheable and page without breaking web."""

from datetime import timedelta

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    GridSpec,
    Scene,
    ScoutDecision,
    ScoutRoute,
    Shoot,
    ShootReceipt,
    ShootRecord,
    ShootStatus,
    Shot,
    ShotKind,
    ShotStatus,
    User,
    now,
)
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
            assert (
                snapshot.json()["latest_shot"]["shot"]["id"]
                == snapshot.json()["recent_shots"][0]["id"]
            )
            assert snapshot.json()["latest_shot"]["analysis"] is None
            etag = snapshot.headers["ETag"]
            unchanged = client.get("/api/mobile/snapshot", headers={"If-None-Match": etag})
            assert unchanged.status_code == 304
            assert unchanged.content == b""
    finally:
        main.app.dependency_overrides.clear()


async def test_shot_detail_exposes_its_run_and_resumes_a_legacy_ingest(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "legacy-mobile-reader"
    await repo.put_user(ctx.store, User(id=user_id, email="legacy@example.test"))
    await repo.put_shot(
        ctx.store,
        Shot(
            id="legacy-shot",
            user_id=user_id,
            kind=ShotKind.PHOTO,
            filename="IMG_legacy.jpg",
            mime_type="image/jpeg",
            status=ShotStatus.INGESTED,
            grid=GridSpec(cols=7, rows=9, width=900, height=1200),
        ),
    )
    await repo.put_shot(
        ctx.store,
        Shot(
            id="unreadable-shot",
            user_id=user_id,
            kind=ShotKind.PHOTO,
            filename="broken.jpg",
            mime_type="image/jpeg",
            status=ShotStatus.FAILED,
            error="image bytes cannot be decoded",
        ),
    )
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            before = client.get("/api/shots/legacy-shot")
            resumed = client.post("/api/shots/legacy-shot/retry")
            after = client.get("/api/shots/legacy-shot")
            terminal = client.post("/api/shots/unreadable-shot/retry")
    finally:
        main.app.dependency_overrides.clear()

    assert before.status_code == 200, before.text
    assert before.json()["run"] is None
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["run"]["shot_id"] == "legacy-shot"
    assert resumed.json()["run"]["steps"]["ingest"]["state"] == "completed"
    assert after.json()["run"]["id"] == resumed.json()["run"]["id"]
    assert terminal.status_code == 409
    assert terminal.json()["detail"] == "This Shot is terminally unreadable"
    events = await repo.list_events(ctx.store, user_id)
    assert [event.stage for event in events].count("resume_requested") == 1


async def test_mobile_snapshot_exposes_current_shoot_and_newest_record_in_etag(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "shoot-mobile-reader"
    await repo.put_user(ctx.store, User(id=user_id, email="shoot-reader@example.test"))
    at = now()
    scene = Scene(
        id="scene_mobile",
        user_id=user_id,
        shoot_id="shoot_mobile",
        ordered_shot_ids=["shoot-shot-1", "shoot-shot-2"],
        started_at=at,
        ended_at=at + timedelta(minutes=2),
    )
    shoot = Shoot(
        id="shoot_mobile",
        user_id=user_id,
        status=ShootStatus.CLOSING,
        ordered_scene_ids=[scene.id],
        ordered_shot_ids=list(scene.ordered_shot_ids),
        started_at=at,
        last_capture_at=scene.ended_at,
    )
    await repo.put_scene(ctx.store, scene)
    await repo.put_shoot(ctx.store, shoot)

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            processing = client.get("/api/mobile/snapshot")
            assert processing.status_code == 200, processing.text
            assert processing.json()["latest_shoot"]["id"] == shoot.id
            assert processing.json()["latest_shoot"]["status"] == "closing"
            assert processing.json()["latest_shoot_record"] is None
            processing_etag = processing.headers["ETag"]

            record = ShootRecord(
                shoot_id=shoot.id,
                user_id=user_id,
                scene_ids=[scene.id],
                shot_ids=list(scene.ordered_shot_ids),
                receipt=ShootReceipt(
                    calc_version="shoot-receipt-1+tendency-2",
                    summary="2 Shots across 1 Scene.",
                    shot_count=2,
                    scene_count=1,
                    shots_per_scene=[2],
                    repeated=["2 of 2 readable Shots used portrait orientation (measured)."],
                ),
                scout=ScoutDecision(
                    route=ScoutRoute.EXPLAIN,
                    reason="The receipt has a supported pattern.",
                    input_shot_ids=list(scene.ordered_shot_ids),
                    policy_version="shoot-scout-1",
                ),
                settled_at=at + timedelta(minutes=5),
            )
            await repo.put_shoot_record_once(ctx.store, record)
            shoot.status = ShootStatus.SETTLED
            shoot.current_record_revision = 1
            shoot.closed_at = record.settled_at
            await repo.put_shoot(ctx.store, shoot)

            settled = client.get(
                "/api/mobile/snapshot",
                headers={"If-None-Match": processing_etag},
            )
            assert settled.status_code == 200, settled.text
            assert settled.headers["ETag"] != processing_etag
            body = settled.json()
            assert body["latest_shoot"]["status"] == "settled"
            assert body["latest_shoot_record"]["shoot_id"] == shoot.id
            assert body["latest_shoot_record"]["receipt"]["shot_count"] == 2
            assert body["latest_shoot_record"]["scout"]["route"] == "explain"
            assert "overall_score" not in body["latest_shoot_record"]["receipt"]
    finally:
        main.app.dependency_overrides.clear()


async def test_mobile_snapshot_pairs_latest_shoot_with_its_record_when_older_shoot_finishes_last(
    tmp_path,
):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "out-of-order-shoot-reader"
    await repo.put_user(ctx.store, User(id=user_id, email="out-of-order@example.test"))
    at = now()
    older = Shoot(
        id="shoot_older",
        user_id=user_id,
        status=ShootStatus.SETTLED,
        started_at=at - timedelta(days=1),
        last_capture_at=at - timedelta(days=1, minutes=-2),
        current_record_revision=1,
        closed_at=at + timedelta(minutes=10),
    )
    newer = Shoot(
        id="shoot_newer",
        user_id=user_id,
        status=ShootStatus.SETTLED,
        started_at=at,
        last_capture_at=at + timedelta(minutes=2),
        current_record_revision=1,
        closed_at=at + timedelta(minutes=5),
    )
    await repo.put_shoot(ctx.store, older)
    await repo.put_shoot(ctx.store, newer)

    def record(shoot: Shoot, settled_at) -> ShootRecord:
        return ShootRecord(
            shoot_id=shoot.id,
            user_id=user_id,
            revision=1,
            receipt=ShootReceipt(
                calc_version="shoot-receipt-1+tendency-2",
                summary="This outing is ready.",
            ),
            scout=ScoutDecision(
                route=ScoutRoute.SILENCE,
                reason="Nothing needs attention.",
                policy_version="shoot-scout-3",
            ),
            settled_at=settled_at,
        )

    await repo.put_shoot_record_once(ctx.store, record(newer, newer.closed_at))
    await repo.put_shoot_record_once(ctx.store, record(older, older.closed_at))

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            response = client.get("/api/mobile/snapshot")
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["latest_shoot"]["id"] == newer.id
    assert body["latest_shoot_record"]["shoot_id"] == newer.id
