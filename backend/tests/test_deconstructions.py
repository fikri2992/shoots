"""Deconstruction through the real API, Store, BlobStore, and Pillow renderer."""

import hashlib
import re
from datetime import timedelta
from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageStat

from app.agents import prompts
from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    Analysis,
    Composition,
    Criteria,
    DeconstructionBeat,
    DeconstructionSourceType,
    DeconstructionStory,
    DeconstructionWriting,
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
    VisualArtifactAuthority,
    VisualArtifactKind,
    VisualArtifactStatus,
    VisualArtifactVerification,
    now,
)
from app.imaging import canvas, visual_evidence
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import (
    ORIGINAL,
    LocalBlobStore,
    blob_path,
    deconstruction_blob_path,
    visual_evidence_blob_path,
)
from app.infra.store import InMemoryStore
from app.services import deconstructions, scout
from app.services.context import Context

VISIBLE_STORY_JARGON = re.compile(
    r"\b(keeper|criteria|verdict|record|corroborated|analyst|evidence|revision|score)\b",
    re.IGNORECASE,
)


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
        ImageDraw.Draw(frame).rectangle((180, 400, 315, 550), fill=(238, 125, 93))
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
                observations=[
                    "A small coral rectangle occupies B3-C3 against a broad blue field.",
                    "Straight sides surround a flat block of coral.",
                    "Blue space extends above and below the coral rectangle.",
                    "The coral block sits left of the middle of the image.",
                    "The orange-red block contrasts with the surrounding blue.",
                    "The background has an even blue tone.",
                ],
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


async def seed_writing(
    ctx: Context,
    user_id: str,
    source_type: str = "shoot",
    source_id: str = "shoot_walk",
    cover_id: str = "shot_1",
    beat_count: int = 2,
):
    """Hand-authored checkpoint fixture, NOT a mocked agent or live model result.

    These tests exercise the real API's recovery/render/export boundary. Real
    fresh model writing is exercised by scripts/check_deconstruction_quality.py.
    """
    waiting = await deconstructions.prepare(
        ctx, user_id, DeconstructionSourceType(source_type), source_id, 1
    )
    cover = await repo.get_shot(ctx.store, cover_id)
    analysis = await repo.find_analysis(ctx.store, cover_id)
    original_bytes = await ctx.blobs.read(cover.blobs[ORIGINAL])
    evidence, _ = await deconstructions.load_story_evidence(
        ctx, cover, analysis, original_bytes, canvas.load_bytes(original_bytes)
    )
    details = [
        ("Straight sides", "Straight sides close around a flat block of coral."),
        ("Blue around coral", "Blue space extends above and below the small coral rectangle."),
        ("Left of centre", "The small block leaves more room on its right."),
        ("Two colours meet", "Coral separates from the blue surrounding it."),
        ("An even field", "The broad blue background holds one even tone."),
    ]
    story = DeconstructionStory(
        opening=DeconstructionBeat(
            title="Coral in blue",
            body="A small coral rectangle interrupts a broad blue field.",
            evidence_ids=["observation_1"],
        ),
        beats=[
            DeconstructionBeat(
                title=title,
                body=body,
                evidence_ids=["observation_1", f"observation_{index + 2}"],
                detail_evidence_id="observation_1" if index == 0 else "",
            )
            for index, (title, body) in enumerate(details[:beat_count])
        ],
        caption="Coral and blue, with room around the small rectangle.",
        caption_evidence_ids=["observation_1", "observation_3"],
    )
    waiting.writing = DeconstructionWriting(
        input_digest=deconstructions.writing_input_digest(
            DeconstructionSourceType(source_type),
            source_id,
            1,
            cover,
            analysis,
            original_bytes,
            evidence,
        ),
        cover_shot_id=cover_id,
        model="integration-checkpoint-fixture-no-model-call",
        prompt_version=prompts.version("deconstruction"),
        story=story,
        evidence=evidence,
    )
    await repo.put_deconstruction(ctx.store, waiting)
    return waiting


async def test_shot_stories_render_without_keepers_or_settlement_and_reopen_separately(tmp_path):
    ctx, user_id = await seed(tmp_path)
    journey_draft = await seed_writing(ctx, user_id)
    # Neither Shot is a Keeper and neither has an aggregate Record.
    for shot_id in ("shot_1", "shot_2"):
        shot = await repo.get_shot(ctx.store, shot_id)
        shot.kept_at = None
        await repo.put_shot(ctx.store, shot)
    for row in await ctx.store.query(repo.SHOOT_RECORDS):
        await ctx.store.delete(
            repo.SHOOT_RECORDS, repo.shoot_record_id(row["shoot_id"], row["revision"])
        )
    before = {
        name: await ctx.store.query(name)
        for name in (repo.SHOTS, repo.ANALYSES, repo.TECHNIQUE_STATES, repo.JOURNEY)
    }
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            # Read-only discovery does not create even an empty draft.
            assert client.get("/api/deconstructions?shot_id=shot_2").json() is None
            assert len(await ctx.store.query(repo.DECONSTRUCTIONS)) == 1
            drafts = []
            for shot_id in ("shot_1", "shot_2"):
                await seed_writing(ctx, user_id, "shot", shot_id, shot_id)
                request = {
                    "source_type": "shot",
                    "source_id": shot_id,
                    "source_revision": 1,
                    "cover_shot_id": shot_id,
                }
                response = client.post("/api/deconstructions", json=request)
                assert response.status_code == 200, response.text
                draft = response.json()
                drafts.append(draft)
                assert draft["status"] == "drafted"
                assert draft["cover_shot_id"] == shot_id
                assert all(page["shot_ids"] == [shot_id] for page in draft["pages"])
                for page in draft["pages"]:
                    assert client.get(f"/api/blobs/{page['blob_path']}").status_code == 200
                assert client.post("/api/deconstructions", json=request).json() == draft
                assert client.get(f"/api/deconstructions?shot_id={shot_id}").json() == draft
            assert drafts[0]["id"] != drafts[1]["id"]
            assert client.get("/api/deconstructions?shot_id=shot_1").json() == drafts[0]
            # Existing web/Android Journey still sees its aggregate draft.
            snapshot = client.get("/api/mobile/snapshot").json()
            assert snapshot["latest_deconstruction"]["id"] == journey_draft.id
            events = await ctx.store.query(repo.EVENTS)
            assert {
                event["shot_id"] for event in events if event["stage"] == "deconstruction_drafted"
            } == {"shot_1", "shot_2"}
    finally:
        main.app.dependency_overrides.clear()
    for name, rows in before.items():
        assert await ctx.store.query(name) == rows


@pytest.mark.parametrize(
    ("fault", "status"),
    [
        ("foreign", 404),
        ("missing", 404),
        ("inspiration", 404),
        ("video", 409),
        ("original", 409),
        ("analysis", 409),
        ("abstained", 409),
        ("cover", 409),
        ("revision", 409),
    ],
)
async def test_shot_story_rejects_unavailable_or_mismatched_source(tmp_path, fault, status):
    ctx, user_id = await seed(tmp_path)
    shot = await repo.get_shot(ctx.store, "shot_2")
    if fault == "foreign":
        shot.user_id = "another_photographer"
    elif fault == "inspiration":
        shot.superseded_by_inspiration_id = "inspiration_2"
    elif fault == "video":
        shot.kind = ShotKind.VIDEO
    elif fault == "original":
        shot.blobs.clear()
    await repo.put_shot(ctx.store, shot)
    if fault == "analysis":
        await ctx.store.delete(repo.ANALYSES, shot.id)
    elif fault == "abstained":
        analysis = await repo.find_analysis(ctx.store, shot.id)
        analysis.abstained = "No usable reading"
        await repo.put_analysis(ctx.store, analysis)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            source_id = "missing" if fault == "missing" else shot.id
            response = client.post(
                "/api/deconstructions",
                json={
                    "source_type": "shot",
                    "source_id": source_id,
                    "source_revision": 0 if fault == "revision" else 1,
                    "cover_shot_id": "shot_1" if fault == "cover" else source_id,
                },
            )
            assert response.status_code == status, response.text
            if status == 404:
                assert client.get(f"/api/deconstructions?shot_id={source_id}").status_code == 404
            assert not (await repo.get_shot(ctx.store, shot.id)).kept_at
            assert all(not row["pages"] for row in await ctx.store.query(repo.DECONSTRUCTIONS))
    finally:
        main.app.dependency_overrides.clear()


async def test_deconstruction_requires_photographer_cover_then_renders_idempotently(tmp_path):
    ctx, user_id = await seed(tmp_path)
    await seed_writing(ctx, user_id)
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
            assert "marked" in refused.json()["detail"]
            assert "Keeper" not in refused.json()["detail"]

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
            assert all(body["input_digest"][:12] in page["blob_path"] for page in body["pages"])
            detail = next(page for page in body["pages"] if page["kind"] == "story")
            assert detail["visual_layer"] == "detail"
            assert detail["detail_cells"] == ["B3", "C3"]
            visible_words = " ".join(
                [body["suggested_caption"]]
                + [part for page in body["pages"] for part in (page["title"], page["claim"])]
            )
            assert [page["title"] for page in body["pages"]] == [
                "Coral in blue",
                "Straight sides",
                "Blue around coral",
                "",
            ]
            assert VISIBLE_STORY_JARGON.search(visible_words) is None
            assert re.search(r"\b[A-H][1-6]\b", visible_words) is None
            for page in body["pages"]:
                data = await ctx.blobs.read(page["blob_path"])
                image_download = client.get(f"/api/blobs/{page['blob_path']}")
                assert image_download.status_code == 200
                assert image_download.headers["content-type"] == "image/jpeg"
                assert image_download.content == data
                with Image.open(BytesIO(image_download.content)) as rendered:
                    assert rendered.size == (
                        (900, 1200) if page["kind"] == "clean" else (1080, 1350)
                    )
            assert all(page["shot_ids"] == ["shot_1"] for page in body["pages"])
            original = canvas.load_bytes(
                await ctx.blobs.read((await repo.get_shot(ctx.store, "shot_1")).blobs[ORIGINAL])
            )
            clean = canvas.load_bytes(await ctx.blobs.read(body["pages"][-1]["blob_path"]))
            assert max(ImageStat.Stat(ImageChops.difference(original, clean)).mean) < 1
            assert not clean.getexif()

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

            download = client.get(f"/api/deconstructions/{body['id']}/download")
            assert download.status_code == 200
            assert download.headers["content-type"] == "application/zip"
            with ZipFile(BytesIO(download.content)) as story:
                assert story.namelist() == [
                    "story-01.jpg",
                    "story-02.jpg",
                    "story-03.jpg",
                    "story-04.jpg",
                    "caption.txt",
                ]
                assert story.read("caption.txt").decode() == body["suggested_caption"]

            snapshot = client.get("/api/mobile/snapshot")
            assert snapshot.status_code == 200
            assert snapshot.json()["latest_deconstruction"]["id"] == body["id"]

            main.app.dependency_overrides[current_user] = lambda: {"id": "another_user"}
            for page in body["pages"]:
                assert client.get(f"/api/blobs/{page['blob_path']}").status_code == 404
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
    await seed_writing(ctx, user_id, "experiment", experiment.id)

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
        "story",
        "story",
        "clean",
    ]
    assert [page["title"] for page in body["pages"]] == [
        "Coral in blue",
        "Straight sides",
        "Blue around coral",
        "",
    ]
    assert (await repo.find_experiment(ctx.store, experiment.id)).verdicts == experiment.verdicts
    visible_words = " ".join(
        [body["suggested_caption"]]
        + [part for page in body["pages"] for part in (page["title"], page["claim"])]
    )
    assert VISIBLE_STORY_JARGON.search(visible_words) is None
    assert all(page["evidence_refs"] for page in body["pages"])
    for page in body["pages"]:
        with Image.open(BytesIO(await ctx.blobs.read(page["blob_path"]))) as rendered:
            assert rendered.size == ((900, 1200) if page["kind"] == "clean" else (1080, 1350))


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
    assert outcome == "Shoots checked the result and found no useful next idea."
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
    await seed_writing(ctx, user_id, "experiment", experiment.id, "shot_2")

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
    assert all(page["shot_ids"] == ["shot_2"] for page in pages)
    assert pages[-1]["kind"] == "clean"
    stored = await repo.find_experiment(ctx.store, experiment.id)
    assert stored.verdicts == []
    assert stored.variation_observations == experiment.variation_observations
    visible = " ".join(part for page in pages for part in (page["title"], page["claim"]))
    assert VISIBLE_STORY_JARGON.search(visible) is None
    assert "winner" not in visible.lower()


@pytest.mark.parametrize("beat_count", [1, 5])
async def test_variable_carousel_length_and_landscape_clean_ending(tmp_path, beat_count):
    ctx, user_id = await seed(tmp_path)
    shot = await repo.get_shot(ctx.store, "shot_1")
    # A real landscape original with distinct corner colours detects a forced crop.
    original = Image.new("RGB", (1600, 600), (40, 70, 120))
    draw = ImageDraw.Draw(original)
    draw.rectangle((0, 0, 90, 90), fill=(255, 30, 30))
    draw.rectangle((1510, 510, 1599, 599), fill=(30, 255, 30))
    source_bytes = canvas.to_jpeg_bytes(original, quality=95)
    await ctx.blobs.write(shot.blobs[ORIGINAL], source_bytes, "image/jpeg")
    await seed_writing(ctx, user_id, beat_count=beat_count)
    analyses_before = await ctx.store.query(repo.ANALYSES)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/api/deconstructions",
                json={
                    "source_type": "shoot",
                    "source_id": "shoot_walk",
                    "source_revision": 1,
                    "cover_shot_id": "shot_1",
                },
            )
            assert response.status_code == 200, response.text
            pages = response.json()["pages"]
            assert len(pages) == beat_count + 2
            clean = canvas.load_bytes(client.get(f"/api/blobs/{pages[-1]['blob_path']}").content)
            assert clean.size == (1600, 600)
            assert clean.getpixel((10, 10))[0] > 240
            assert clean.getpixel((1590, 590))[1] > 240
            assert not pages[-1]["title"] and not pages[-1]["claim"]
    finally:
        main.app.dependency_overrides.clear()
    assert await ctx.blobs.read(shot.blobs[ORIGINAL]) == source_bytes
    assert await ctx.store.query(repo.ANALYSES) == analyses_before


async def test_real_render_failure_retains_checkpoint_and_recovers_without_a_writer(tmp_path):
    ctx, user_id = await seed(tmp_path)
    waiting = await seed_writing(ctx, user_id)
    digest = deconstructions._render_digest(waiting.writing)
    path = deconstruction_blob_path(user_id, waiting.id, 2, digest)
    # A real filesystem collision, not a mocked failed BlobStore call.
    obstruction = ctx.blobs.root / path
    obstruction.mkdir(parents=True)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    request = {
        "source_type": "shoot",
        "source_id": "shoot_walk",
        "source_revision": 1,
        "cover_shot_id": "shot_1",
    }
    try:
        with TestClient(main.app) as client:
            failed = client.post("/api/deconstructions", json=request)
            assert failed.status_code == 503
            stored = client.get(f"/api/deconstructions/{waiting.id}").json()
            assert stored["status"] == "failed"
            assert stored["writing"]["story"] == waiting.writing.story.model_dump()
            assert stored["error"]
            obstruction.rmdir()
            recovered = client.post("/api/deconstructions", json=request)
            assert recovered.status_code == 200, recovered.text
            assert recovered.json()["status"] == "drafted"
            assert recovered.json()["error"] == ""
            assert recovered.json()["writing"] == waiting.writing.model_dump(mode="json")
            # A missing generated file also resumes rendering from this checkpoint.
            missing = recovered.json()["pages"][2]["blob_path"]
            await ctx.blobs.delete(missing)
            repaired = client.post("/api/deconstructions", json=request)
            assert repaired.status_code == 200
            assert client.get(f"/api/blobs/{missing}").status_code == 200
    finally:
        main.app.dependency_overrides.clear()
    events = await ctx.store.query(repo.EVENTS)
    assert not any(event["stage"] == "deconstruction_writing" for event in events)
    assert any(event["stage"] == "deconstruction_failed" for event in events)


@pytest.mark.parametrize("invalid", ["foreign_reference", "invented_intent", "inferred_time"])
async def test_invalid_checkpoint_is_visible_and_never_replaced_by_template_prose(
    tmp_path, invalid
):
    ctx, user_id = await seed(tmp_path)
    waiting = await seed_writing(ctx, user_id)
    if invalid == "foreign_reference":
        waiting.writing.story.beats[0].evidence_ids = ["other_shot_observation"]
    elif invalid == "invented_intent":
        waiting.writing.story.opening.title = "I wanted this moment"
    else:
        waiting.writing.story.opening.title = "Blue at dawn"
    await repo.put_deconstruction(ctx.store, waiting)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/api/deconstructions",
                json={
                    "source_type": "shoot",
                    "source_id": "shoot_walk",
                    "source_revision": 1,
                    "cover_shot_id": "shot_1",
                },
            )
            assert response.status_code == 503
            stored = client.get(f"/api/deconstructions/{waiting.id}").json()
            assert stored["status"] == "failed"
            assert stored["pages"] == []
            assert stored["error"]
    finally:
        main.app.dependency_overrides.clear()


async def test_active_writer_lease_blocks_overlap_but_expired_work_can_resume(tmp_path):
    ctx, user_id = await seed(tmp_path)
    waiting = await seed_writing(ctx, user_id)
    await ctx.store.patch_if(
        repo.DECONSTRUCTIONS,
        waiting.id,
        {
            "_writing_token": "earlier-request",
            "_writing_until": (now() + timedelta(minutes=2)).isoformat(),
        },
        {},
    )
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    request = {
        "source_type": "shoot",
        "source_id": "shoot_walk",
        "source_revision": 1,
        "cover_shot_id": "shot_1",
    }
    try:
        with TestClient(main.app) as client:
            assert client.post("/api/deconstructions", json=request).status_code == 409
            background = await deconstructions.prepare(
                ctx, user_id, DeconstructionSourceType.SHOOT, "shoot_walk", 1
            )
            assert background.writing == waiting.writing
            raw = await ctx.store.get(repo.DECONSTRUCTIONS, waiting.id)
            assert raw["_writing_token"] == "earlier-request"
            await ctx.store.patch_if(
                repo.DECONSTRUCTIONS,
                waiting.id,
                {
                    "_writing_until": (now() - timedelta(seconds=1)).isoformat(),
                },
                {},
            )
            response = client.post("/api/deconstructions", json=request)
            assert response.status_code == 200, response.text
            assert "_writing_token" not in response.json()
    finally:
        main.app.dependency_overrides.clear()
    assert (await ctx.store.get(repo.DECONSTRUCTIONS, waiting.id))["_writing_token"] == ""


async def test_failed_cover_change_preserves_old_images_and_resumes_the_new_story(tmp_path):
    ctx, user_id = await seed(tmp_path)
    await seed_writing(ctx, user_id)
    first = await deconstructions.prepare(
        ctx, user_id, DeconstructionSourceType.SHOOT, "shoot_walk", 1, "shot_1"
    )
    old_bytes = [await ctx.blobs.read(page.blob_path) for page in first.pages]
    second = await repo.get_shot(ctx.store, "shot_2")
    second.kept_at = now()
    await repo.put_shot(ctx.store, second)
    checkpoint = await seed_writing(ctx, user_id, cover_id="shot_2")
    digest = deconstructions._render_digest(checkpoint.writing)
    obstruction = ctx.blobs.root / deconstruction_blob_path(user_id, first.id, 2, digest)
    obstruction.mkdir(parents=True)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    request = {
        "source_type": "shoot",
        "source_id": "shoot_walk",
        "source_revision": 1,
        "cover_shot_id": "shot_2",
    }
    try:
        with TestClient(main.app) as client:
            failed = client.post("/api/deconstructions", json=request)
            assert failed.status_code == 503
            retained = client.get(f"/api/deconstructions/{first.id}").json()
            assert retained["status"] == "drafted"
            assert retained["cover_shot_id"] == "shot_1"
            assert retained["error"]
            assert retained["pages"] == [page.model_dump(mode="json") for page in first.pages]
            obstruction.rmdir()
            recovered = client.post("/api/deconstructions", json=request)
            assert recovered.status_code == 200, recovered.text
            assert recovered.json()["cover_shot_id"] == "shot_2"
            assert all(page["shot_ids"] == ["shot_2"] for page in recovered.json()["pages"])
            for page, original_bytes in zip(first.pages, old_bytes, strict=True):
                assert client.get(f"/api/blobs/{page.blob_path}").content == original_bytes
    finally:
        main.app.dependency_overrides.clear()


async def seed_visual_artifact(ctx: Context, user_id: str, fault: str = "") -> str:
    """Real OpenCV hue measurement on the integration image, never an agent mock."""
    shot = await repo.get_shot(ctx.store, "shot_1")
    analysis = await repo.find_analysis(ctx.store, shot.id)
    source_bytes = await ctx.blobs.read(shot.blobs[ORIGINAL])
    technique = TechniqueEvidence(
        technique_id="warm_cool",
        confidence=0.88,
        agreement=2,
        note="The small coral rectangle contrasts with its broad blue surroundings.",
    )
    result = visual_evidence.render(
        canvas.load_bytes(source_bytes),
        shot,
        technique,
        hashlib.sha256(source_bytes).hexdigest()[:24],
    )
    assert result.image is not None
    artifact = result.artifact
    path = visual_evidence_blob_path(user_id, shot.id, technique.technique_id)
    payload = canvas.to_jpeg_bytes(result.image)
    if fault == "fallback":
        artifact.status = VisualArtifactStatus.FALLBACK
    elif fault == "rejected":
        artifact.verification = VisualArtifactVerification.REJECTED
    elif fault == "not_run":
        artifact.verification = VisualArtifactVerification.NOT_RUN
    elif fault == "manual_fixture":
        artifact.authority = VisualArtifactAuthority.MANUAL_FIXTURE
    elif fault == "unresolved":
        artifact.authority = VisualArtifactAuthority.UNRESOLVED
    elif fault == "stale_source":
        artifact.source_digest = "different-original"
    elif fault == "stale_renderer":
        artifact.renderer_version = "old-renderer"
    elif fault == "foreign_user":
        path = visual_evidence_blob_path("other_user", shot.id, technique.technique_id)
    elif fault == "wrong_shot":
        path = visual_evidence_blob_path(user_id, "shot_2", technique.technique_id)
    elif fault == "corrupt_file":
        payload = b"unreadable image bytes"
    elif fault == "wrong_frame":
        payload = canvas.to_jpeg_bytes(result.image.resize((64, 64)))
    artifact.blob_path = path if fault != "no_image" else ""
    if fault not in {"missing_file", "no_image"}:
        await ctx.blobs.write(path, payload, "image/jpeg")
    technique.visual_artifact = artifact
    analysis.techniques.append(technique)
    await repo.put_analysis(ctx.store, analysis)
    return "technique_warm_cool"


async def seed_artifact_writing(ctx: Context, user_id: str):
    waiting = await seed_writing(ctx, user_id)
    beat = waiting.writing.story.beats[0]
    beat.title = "Coral against blue"
    beat.body = "The small coral shape stands apart from the broad blue field."
    beat.evidence_ids = ["observation_1", "technique_warm_cool"]
    beat.detail_evidence_id = ""
    beat.artifact_evidence_id = "technique_warm_cool"
    await repo.put_deconstruction(ctx.store, waiting)
    return waiting


@pytest.mark.parametrize("landscape", [False, True])
async def test_existing_artifact_and_story_share_the_export_without_changing_source(
    tmp_path, landscape
):
    ctx, user_id = await seed(tmp_path)
    shot = await repo.get_shot(ctx.store, "shot_1")
    if landscape:
        source = canvas.load_bytes(await ctx.blobs.read(shot.blobs[ORIGINAL]))
        await ctx.blobs.write(
            shot.blobs[ORIGINAL], canvas.to_jpeg_bytes(source.resize((1600, 800))), "image/jpeg"
        )
        shot.grid = GridSpec(cols=8, rows=6, width=1600, height=800)
        await repo.put_shot(ctx.store, shot)
    await seed_visual_artifact(ctx, user_id)
    checkpoint = await seed_artifact_writing(ctx, user_id)
    source_bytes = await ctx.blobs.read(shot.blobs[ORIGINAL])
    analyses_before = await ctx.store.query(repo.ANALYSES)
    selected = next(
        item for item in checkpoint.writing.evidence if item.id == "technique_warm_cool"
    )
    artifact_bytes = await ctx.blobs.read(selected.visual_artifact.blob_path)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            request = {
                "source_type": "shoot",
                "source_id": "shoot_walk",
                "source_revision": 1,
                "cover_shot_id": "shot_1",
            }
            response = client.post("/api/deconstructions", json=request)
            assert response.status_code == 200, response.text
            pages = response.json()["pages"]
            page = pages[1]
            assert page["visual_layer"] == "artifact"
            assert page["artifact_evidence_id"] == selected.id
            assert page["artifact_sha256"] == hashlib.sha256(artifact_bytes).hexdigest()
            assert any(page["artifact_sha256"] in ref for ref in page["evidence_refs"])
            assert not page["detail_cells"]
            for clean_page in (pages[0], pages[-1]):
                assert clean_page["visual_artifact"] is None
                assert not clean_page["artifact_evidence_id"]
            exported = canvas.load_bytes(client.get(f"/api/blobs/{page['blob_path']}").content)
            assert exported.size == (1080, 1350)
            boxes = (
                ((32, 246, 1048, 562), (32, 610, 1048, 926))
                if landscape
                else ((32, 256, 528, 938), (552, 256, 1048, 938))
            )
            for box, data in zip(boxes, [source_bytes, artifact_bytes], strict=True):
                width, height = box[2] - box[0], box[3] - box[1]
                expected = Image.new("RGB", (width, height), (16, 17, 16))
                fitted = ImageOps.contain(
                    canvas.load_bytes(data), (width, height), Image.Resampling.LANCZOS
                )
                expected.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
                difference = ImageStat.Stat(
                    ImageChops.difference(expected, exported.crop(box))
                ).mean
                assert max(difference) < 2, difference
            clean = canvas.load_bytes(client.get(f"/api/blobs/{pages[-1]['blob_path']}").content)
            assert clean.size == ((1600, 800) if landscape else (900, 1200))
            snapshot = client.get("/api/mobile/snapshot").json()["latest_deconstruction"]
            assert snapshot["pages"][1]["blob_path"] == page["blob_path"]
            assert client.post("/api/deconstructions", json=request).json() == response.json()
    finally:
        main.app.dependency_overrides.clear()
    assert await ctx.store.query(repo.ANALYSES) == analyses_before
    assert await ctx.blobs.read(shot.blobs[ORIGINAL]) == source_bytes
    assert await ctx.blobs.read(selected.visual_artifact.blob_path) == artifact_bytes


@pytest.mark.parametrize(
    "fault",
    [
        "fallback",
        "rejected",
        "not_run",
        "manual_fixture",
        "unresolved",
        "stale_source",
        "stale_renderer",
        "foreign_user",
        "wrong_shot",
        "missing_file",
        "corrupt_file",
        "wrong_frame",
        "no_image",
    ],
)
async def test_unusable_artifact_is_not_offered_or_substituted_into_export(tmp_path, fault):
    ctx, user_id = await seed(tmp_path)
    await seed_visual_artifact(ctx, user_id, fault)
    checkpoint = await seed_artifact_writing(ctx, user_id)
    evidence = next(
        item for item in checkpoint.writing.evidence if item.id == "technique_warm_cool"
    )
    assert evidence.visual_artifact is None and not evidence.artifact_sha256
    analyses_before = await ctx.store.query(repo.ANALYSES)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user_id}
    try:
        with TestClient(main.app) as client:
            request = {
                "source_type": "shoot",
                "source_id": "shoot_walk",
                "source_revision": 1,
                "cover_shot_id": "shot_1",
            }
            refused = client.post("/api/deconstructions", json=request)
            assert refused.status_code == 503
            assert "unavailable visual artifact" in refused.json()["detail"]
            assert (await repo.find_deconstruction(ctx.store, checkpoint.id)).pages == []
            # A writer can still choose a supported full-frame beat when no artifact fits.
            checkpoint.writing.story.beats[0].artifact_evidence_id = ""
            await repo.put_deconstruction(ctx.store, checkpoint)
            recovered = client.post("/api/deconstructions", json=request)
            assert recovered.status_code == 200, recovered.text
            assert recovered.json()["pages"][1]["visual_layer"] == "original"
    finally:
        main.app.dependency_overrides.clear()
    assert await ctx.store.query(repo.ANALYSES) == analyses_before


@pytest.mark.parametrize("fault", ["uncited", "combined", "opening"])
async def test_artifact_selection_must_match_cited_story_and_leave_cover_clean(tmp_path, fault):
    ctx, user_id = await seed(tmp_path)
    await seed_visual_artifact(ctx, user_id)
    checkpoint = await seed_artifact_writing(ctx, user_id)
    if fault == "uncited":
        checkpoint.writing.story.beats[0].evidence_ids = ["observation_1"]
    elif fault == "combined":
        checkpoint.writing.story.beats[0].detail_evidence_id = "observation_1"
    else:
        checkpoint.writing.story.opening.artifact_evidence_id = "technique_warm_cool"
    await repo.put_deconstruction(ctx.store, checkpoint)
    with pytest.raises(deconstructions.DeconstructionUnavailable):
        await deconstructions.prepare(
            ctx, user_id, DeconstructionSourceType.SHOOT, "shoot_walk", 1, "shot_1"
        )
    stored = await repo.find_deconstruction(ctx.store, checkpoint.id)
    assert stored.error and not stored.pages


async def test_artifact_file_bytes_are_part_of_the_persisted_writer_inputs(tmp_path):
    ctx, user_id = await seed(tmp_path)
    await seed_visual_artifact(ctx, user_id)
    checkpoint = await seed_artifact_writing(ctx, user_id)
    first = await deconstructions.prepare(
        ctx, user_id, DeconstructionSourceType.SHOOT, "shoot_walk", 1, "shot_1"
    )
    artifact = first.pages[1].visual_artifact
    old_bytes = await ctx.blobs.read(artifact.blob_path)
    # A real, same-framing file replacement must not reuse a stale writer fingerprint.
    replacement = canvas.to_jpeg_bytes(canvas.load_bytes(old_bytes), quality=80)
    assert replacement != old_bytes
    await ctx.blobs.write(artifact.blob_path, replacement, "image/jpeg")
    new_checkpoint = await seed_artifact_writing(ctx, user_id)
    assert new_checkpoint.writing.input_digest != checkpoint.writing.input_digest
    updated = await deconstructions.prepare(
        ctx, user_id, DeconstructionSourceType.SHOOT, "shoot_walk", 1, "shot_1"
    )
    assert updated.pages[1].artifact_sha256 == hashlib.sha256(replacement).hexdigest()
    assert updated.pages[1].blob_path != first.pages[1].blob_path
    assert await ctx.blobs.exists(first.pages[1].blob_path)


@pytest.mark.parametrize("subject", ["small", "broad", "unlocated"])
async def test_measured_contour_cannot_contradict_the_stored_subject_extent(tmp_path, subject):
    ctx, user_id = await seed(tmp_path)
    shot = await repo.get_shot(ctx.store, "shot_1")
    frame = Image.new("RGB", (900, 1200), (20, 30, 40))
    draw = ImageDraw.Draw(frame)
    draw.rectangle((90, 110, 810, 910), fill=(70, 100, 150))
    draw.ellipse((420, 580, 450, 610), fill=(250, 248, 236))
    payload = canvas.to_jpeg_bytes(frame)
    await ctx.blobs.write(shot.blobs[ORIGINAL], payload, "image/jpeg")
    technique = TechniqueEvidence(
        technique_id="fill_the_frame",
        confidence=0.9,
        agreement=2,
        cells=[f"{column}{row}" for column in "ABCDEFGH" for row in range(1, 6)],
        note="A broad blue rectangle fills much of the frame.",
    )
    result = visual_evidence.render(
        canvas.load_bytes(payload), shot, technique, hashlib.sha256(payload).hexdigest()[:24]
    )
    assert result.image is not None
    assert result.artifact.kind is VisualArtifactKind.SUBJECT_CONTOUR
    assert result.artifact.metrics["frame_occupancy_pct"] > 50
    result.artifact.blob_path = visual_evidence_blob_path(user_id, shot.id, technique.technique_id)
    await ctx.blobs.write(
        result.artifact.blob_path, canvas.to_jpeg_bytes(result.image), "image/jpeg"
    )
    technique.visual_artifact = result.artifact
    analysis = await repo.find_analysis(ctx.store, shot.id)
    analysis.techniques = [technique]
    analysis.composition.subject_cells = {"small": ["D4"], "broad": ["A1", "H5"], "unlocated": []}[
        subject
    ]
    await repo.put_analysis(ctx.store, analysis)
    checkpoint = await seed_writing(ctx, user_id)
    selected = next(
        item for item in checkpoint.writing.evidence if item.id == "technique_fill_the_frame"
    )
    assert (selected.visual_artifact is not None) is (subject == "broad")
    beat = checkpoint.writing.story.beats[0]
    beat.evidence_ids = ["technique_fill_the_frame"]
    beat.detail_evidence_id = ""
    beat.artifact_evidence_id = selected.id
    await repo.put_deconstruction(ctx.store, checkpoint)
    if subject == "broad":
        draft = await deconstructions.prepare(
            ctx, user_id, DeconstructionSourceType.SHOOT, "shoot_walk", 1, "shot_1"
        )
        assert draft.pages[1].visual_layer == "artifact"
    else:
        with pytest.raises(deconstructions.DeconstructionUnavailable):
            await deconstructions.prepare(
                ctx, user_id, DeconstructionSourceType.SHOOT, "shoot_walk", 1, "shot_1"
            )
