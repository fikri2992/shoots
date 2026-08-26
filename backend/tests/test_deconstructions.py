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
    Criteria,
    Experiment,
    ExperimentStatus,
    ExperimentType,
    GridSpec,
    Provenance,
    ShootReceipt,
    ShootRecord,
    Shot,
    ShotKind,
    ShotStatus,
    TechniqueEvidence,
    User,
    Variation,
    VariationObservation,
    Verdict,
    now,
)
from app.imaging import canvas
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import ORIGINAL, LocalBlobStore, blob_path
from app.infra.store import InMemoryStore
from app.services import deconstructions, scout
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


async def test_terminal_experiment_requires_cover_then_renders_its_record(tmp_path):
    ctx, user_id = await seed(tmp_path)
    experiment = Experiment(
        id="experiment_share",
        user_id=user_id,
        technique_id="negative_space",
        type=ExperimentType.REPRODUCE,
        title="Repeat negative space",
        brief="Keep one small subject against a broad quiet field.",
        why_now="A marked Keeper showed this decision.",
        criteria=Criteria(vision=["negative_space"]),
        reference_shot_id="shot_1",
        result_shot_ids=["shot_2"],
        verdicts=[Verdict(shot_id="shot_2", criteria_met=True, feedback="Criteria met.")],
        status=ExperimentStatus.COMPLETED,
    )
    await repo.put_experiment(ctx.store, experiment)

    waiting = await deconstructions.prepare_experiment_record(ctx, experiment)
    assert waiting.status.value == "needs_cover"
    assert waiting.source_type.value == "experiment"
    assert waiting.source_revision == 1
    assert waiting.candidate_cover_shot_ids == ["shot_1"]

    mutable = Experiment(
        id="experiment_still_open",
        user_id=user_id,
        technique_id="negative_space",
        type=ExperimentType.EXPLORE,
        title="Still exploring",
        brief="Keep trying Variations.",
        why_now="The Experiment is not terminal.",
        result_shot_ids=["shot_2"],
    )
    await repo.put_experiment(ctx.store, mutable)

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            open_refused = client.post(
                "/api/deconstructions",
                json={
                    "source_type": "experiment",
                    "source_id": mutable.id,
                    "source_revision": 1,
                    "cover_shot_id": "shot_1",
                },
            )
            assert open_refused.status_code == 409
            wrong_revision = client.post(
                "/api/deconstructions",
                json={
                    "source_type": "experiment",
                    "source_id": experiment.id,
                    "source_revision": 0,
                    "cover_shot_id": "shot_1",
                },
            )
            assert wrong_revision.status_code == 409
            drafted = client.post(
                "/api/deconstructions",
                json={
                    "source_type": "experiment",
                    "source_id": experiment.id,
                    "source_revision": 1,
                    "cover_shot_id": "shot_1",
                },
            )
            assert drafted.status_code == 200, drafted.text
            body = drafted.json()
    finally:
        main.app.dependency_overrides.clear()

    assert body["status"] == "drafted"
    assert body["source_type"] == "experiment"
    assert body["cover_shot_id"] == "shot_1"
    assert [page["kind"] for page in body["pages"]] == [
        "cover",
        "reproduce",
        "reproduce",
        "record",
    ]
    assert "1 of 1 recorded Verdicts met" in body["pages"][2]["claim"]
    assert all(page["evidence_refs"] for page in body["pages"])
    for page in body["pages"]:
        with Image.open(BytesIO(await ctx.blobs.read(page["blob_path"]))) as rendered:
            assert rendered.size == (1080, 1350)


async def test_closed_experiment_event_prepares_the_needs_cover_artifact(tmp_path):
    ctx, user_id = await seed(tmp_path)
    experiment = Experiment(
        id="experiment_auto_draft",
        user_id=user_id,
        technique_id="negative_space",
        type=ExperimentType.EXPLORE,
        title="Explore negative space",
        brief="Try several amounts of open space.",
        why_now="The Photographer chose this Technique.",
        result_shot_ids=["shot_2"],
        status=ExperimentStatus.COMPLETED,
    )
    await repo.put_experiment(ctx.store, experiment)

    outcome = await scout.on_experiment_closed(
        ctx,
        {"user_id": user_id, "experiment_id": experiment.id, "shot_id": "shot_2"},
    )

    drafts = await repo.list_deconstructions(ctx.store, user_id)
    assert outcome == "Scout checked the settled result and stayed silent."
    assert len(drafts) == 1
    assert drafts[0].source_id == experiment.id
    assert drafts[0].source_type.value == "experiment"
    assert drafts[0].status.value == "needs_cover"


async def test_explore_deconstruction_preserves_variations_without_a_grade(tmp_path):
    ctx, user_id = await seed(tmp_path)
    keeper = await repo.get_shot(ctx.store, "shot_2")
    keeper.kept_at = now()
    await repo.put_shot(ctx.store, keeper)
    experiment = Experiment(
        id="experiment_explore_share",
        user_id=user_id,
        technique_id="negative_space",
        type=ExperimentType.EXPLORE,
        title="Explore negative space",
        brief="Try clear, restrained, and inverted amounts of open space.",
        why_now="The Photographer chose this Technique.",
        variations=[
            Variation(id="clear", title="Clear", instruction="Use broad open space."),
            Variation(id="invert", title="Invert", instruction="Fill the frame.", inversion=True),
        ],
        result_shot_ids=["shot_1", "shot_2"],
        variation_observations=[
            VariationObservation(variation_id="clear", shot_id="shot_1"),
            VariationObservation(variation_id="invert", shot_id="shot_2"),
        ],
        status=ExperimentStatus.COMPLETED,
    )
    await repo.put_experiment(ctx.store, experiment)
    await deconstructions.prepare_experiment_record(ctx, experiment)

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            rendered = client.post(
                "/api/deconstructions",
                json={
                    "source_type": "experiment",
                    "source_id": experiment.id,
                    "source_revision": 1,
                    "cover_shot_id": "shot_2",
                },
            )
            assert rendered.status_code == 200, rendered.text
            pages = rendered.json()["pages"]
    finally:
        main.app.dependency_overrides.clear()

    assert all(page["kind"] != "reproduce" for page in pages)
    observation = next(page for page in pages if page["title"] == "Variations observed")
    assert "2 result observations across 2 Variations" in observation["claim"]
    assert "No result was graded" in observation["claim"]
    visible = " ".join(page["claim"] for page in pages).lower()
    assert "met criteria" not in visible and "winner" not in visible
