"""Deconstruction through the real API, Store, BlobStore, and Pillow renderer."""

import re
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    Analysis,
    Composition,
    GridSpec,
    Provenance,
    ShootReceipt,
    ShootRecord,
    Shot,
    ShotKind,
    ShotStatus,
    TechniqueEvidence,
    User,
    now,
)
from app.imaging import canvas
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import ORIGINAL, LocalBlobStore, blob_path
from app.infra.store import InMemoryStore
from app.services.context import Context


async def seed(tmp_path) -> tuple[Context, str]:
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "deconstruction_user"
    await repo.put_user(ctx.store, User(id=user_id, email="deconstruction@example.test"))
    for index, kept in enumerate((True, False), 1):
        shot = Shot(
            id=f"shot_{index}",
            user_id=user_id,
            kind=ShotKind.PHOTO,
            filename=f"walk-{index}.jpg",
            mime_type="image/jpeg",
            status=ShotStatus.ANALYZED,
            grid=GridSpec(cols=8, rows=6, width=900, height=1200),
            kept_at=now() if kept else None,
        )
        frame = Image.new("RGB", (900, 1200), (35 * index, 75, 105 + 25 * index))
        path = blob_path(user_id, shot.id, ORIGINAL, "jpg")
        shot.blobs[ORIGINAL] = await ctx.blobs.write(
            path,
            canvas.to_jpeg_bytes(frame),
            "image/jpeg",
        )
        await repo.put_shot(ctx.store, shot)
        await repo.put_analysis(
            ctx.store,
            Analysis(
                shot_id=shot.id,
                user_id=user_id,
                model="gemini-test",
                prompt_version="analyst-test",
                techniques=[
                    TechniqueEvidence(
                        technique_id="negative_space",
                        confidence=0.88,
                        agreement=2,
                        cells=["B2", "C2"],
                        note="Open space isolates the subject.",
                    )
                ],
                composition=Composition(
                    subject_cells=["B2", "C2"],
                    guide="thirds",
                ),
                observations=["A small subject sits against a broad quiet field."],
            ),
        )
    record = ShootRecord(
        shoot_id="shoot_walk",
        user_id=user_id,
        revision=1,
        scene_ids=["scene_walk"],
        shot_ids=["shot_1", "shot_2"],
        receipt=ShootReceipt(
            calc_version="shoot-receipt-test",
            summary="You held a quiet subject placement across two Shots.",
            shot_count=2,
            scene_count=1,
            readable_shot_count=2,
            keeper_shot_ids=["shot_1"],
            repeated=["Negative space appeared in 2 readable Shots."],
            varied=["You changed distance while keeping the subject off-centre."],
        ),
        provenance=Provenance(
            shot_ids=["shot_1", "shot_2"],
            sample_size=2,
            calc_version="shoot-receipt-test",
            analysis_versions={"shot_1": "analyst-test", "shot_2": "analyst-test"},
        ),
    )
    await repo.put_shoot_record_once(ctx.store, record)
    return ctx, user_id


async def test_deconstruction_requires_photographer_cover_then_renders_idempotently(tmp_path):
    ctx, user_id = await seed(tmp_path)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            waiting = client.post(
                "/api/deconstructions",
                json={"source_type": "shoot", "source_id": "shoot_walk", "source_revision": 1},
            )
            assert waiting.status_code == 200
            assert waiting.json()["status"] == "needs_cover"
            assert waiting.json()["candidate_cover_shot_ids"] == ["shot_1"]
            assert waiting.json()["pages"] == []

            refused = client.post(
                "/api/deconstructions",
                json={
                    "source_type": "shoot",
                    "source_id": "shoot_walk",
                    "source_revision": 1,
                    "cover_shot_id": "shot_2",
                },
            )
            assert refused.status_code == 409
            assert "marked Keeper" in refused.json()["detail"]

            drafted = client.post(
                "/api/deconstructions",
                json={
                    "source_type": "shoot",
                    "source_id": "shoot_walk",
                    "source_revision": 1,
                    "cover_shot_id": "shot_1",
                },
            )
            assert drafted.status_code == 200
            body = drafted.json()
            assert body["status"] == "drafted"
            assert body["cover_shot_id"] == "shot_1"
            assert 4 <= len(body["pages"]) <= 7
            assert body["suggested_caption"]
            assert all(page["evidence_refs"] for page in body["pages"])
            composition = next(page for page in body["pages"] if page["kind"] == "composition")
            assert composition["visual_layer"] == "annotated"
            visible_words = " ".join(
                [body["suggested_caption"]]
                + [part for page in body["pages"] for part in (page["title"], page["claim"])]
            )
            assert "score" not in visible_words.lower()
            assert re.search(r"\b[A-H][1-6]\b", visible_words) is None
            for page in body["pages"]:
                data = await ctx.blobs.read(page["blob_path"])
                with Image.open(BytesIO(data)) as rendered:
                    assert rendered.size == (1080, 1350)

            repeated = client.post(
                "/api/deconstructions",
                json={
                    "source_type": "shoot",
                    "source_id": "shoot_walk",
                    "source_revision": 1,
                    "cover_shot_id": "shot_1",
                },
            )
            assert repeated.status_code == 200
            assert repeated.json()["id"] == body["id"]
            assert [page["blob_path"] for page in repeated.json()["pages"]] == [
                page["blob_path"] for page in body["pages"]
            ]

            snapshot = client.get("/api/mobile/snapshot")
            assert snapshot.status_code == 200
            assert snapshot.json()["latest_deconstruction"]["id"] == body["id"]
    finally:
        main.app.dependency_overrides.clear()
