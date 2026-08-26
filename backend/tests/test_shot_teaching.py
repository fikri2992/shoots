"""Shot teaching receipt through the authenticated read API and real Store."""

import re

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    Analysis,
    Composition,
    Finding,
    GridSpec,
    Move,
    MoveKind,
    Shot,
    ShotKind,
    ShotStatus,
    TechniqueEvidence,
    User,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.store import InMemoryStore
from app.services.context import Context


async def test_teaching_receipt_unifies_keep_notice_try_and_visible_check():
    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    user = User(id="teach_user", email="teach@example.test")
    shot = Shot(
        id="teach_shot",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        filename="teach.jpg",
        mime_type="image/jpeg",
        status=ShotStatus.ANALYZED,
        grid=GridSpec(cols=8, rows=6, width=800, height=600),
    )
    await repo.put_user(ctx.store, user)
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="negative_space",
                    confidence=0.9,
                    agreement=2,
                    cells=["B2", "C2"],
                    note=(
                        "Open space around B2-C2 isolates the subject. "
                        "This second sentence belongs in the full Analysis, not the receipt."
                    ),
                )
            ],
            findings=[
                Finding(
                    finding_id="camera_shake",
                    what="Fine edges are soft across the frame",
                    why="1/15 s is below the handheld limit",
                )
            ],
            observations=[
                "The child occupies cells B4 through E9.",
                "A horizontal bamboo pole crosses cells A2 through H2 above the child.",
            ],
            composition=Composition(
                guide="thirds",
                moves=[
                    Move(
                        what="Crop the left edge",
                        kind=MoveKind.CROP,
                        to_cells=["C1", "H6"],
                        reason="Remove the shelf.",
                    ),
                    Move(
                        what="Lower the camera below the beam",
                        kind=MoveKind.CAMERA,
                        reason="Keep the beam from crossing the subject.",
                    ),
                    Move(
                        what="Move the subject right",
                        kind=MoveKind.MOVE,
                        from_cells=["B3"],
                        to_cells=["F3"],
                        reason="Separate the subject from the shelf.",
                    ),
                ],
            ),
        ),
    )
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            response = client.get(f"/api/shots/{shot.id}")
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    teaching = response.json()["teaching"]
    assert teaching["keep_technique_id"] == "negative_space"
    assert teaching["keep_title"] == "Negative space"
    assert teaching["keep_authority"] == "model_read"
    assert "second sentence" not in teaching["keep_proof"]
    assert teaching["notice_finding_id"] == "camera_shake"
    assert teaching["notice_authority"] == "measured"
    assert teaching["try_kind"] == "camera"
    assert teaching["try_text"] == "Lower the camera below the beam."
    assert teaching["visible_check"].startswith("Zoom into one fine edge")
    assert teaching["primary_layer"] == "guide"
    visible = " ".join(
        teaching[key]
        for key in (
            "keep_title",
            "keep_proof",
            "notice_title",
            "notice_proof",
            "try_text",
            "try_reason",
            "visible_check",
        )
    )
    assert re.search(r"\b[A-H][1-6]\b", visible) is None


async def test_model_notice_aligns_with_the_selected_move_and_hides_grid_language():
    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    user = User(id="aligned_user", email="aligned@example.test")
    shot = Shot(
        id="aligned_shot",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        filename="aligned.jpg",
        mime_type="image/jpeg",
        grid=GridSpec(cols=8, rows=6, width=800, height=600),
    )
    await repo.put_user(ctx.store, user)
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=user.id,
            model="gemini-test",
            observations=[
                "The child occupies cells B3 through D6.",
                "A bamboo pole runs across cells A2 through H2 in the upper third.",
            ],
            composition=Composition(
                moves=[
                    Move(
                        what="Lower the camera below the pole",
                        kind=MoveKind.CAMERA,
                        reason="Keep the bamboo pole on row 2 from crossing the view.",
                    )
                ]
            ),
        ),
    )
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            response = client.get(f"/api/shots/{shot.id}")
    finally:
        main.app.dependency_overrides.clear()

    receipt = response.json()["teaching"]
    assert "bamboo pole" in receipt["notice_title"].lower()
    assert "child occupies" not in receipt["notice_title"].lower()
    assert "from across" not in receipt["notice_title"].lower()
    assert "across across" not in receipt["notice_title"].lower()
    assert "cell" not in receipt["notice_title"].lower()
    assert re.search(r"\b[A-H][1-6]\b", receipt["notice_title"]) is None
    assert "row" not in receipt["try_reason"].lower()
    assert "the top of the frame" in receipt["try_reason"].lower()


async def test_located_measured_finding_owns_the_default_visual_layer():
    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    await repo.put_user(ctx.store, User(id="u1", email="located@example.test"))
    shot = Shot(
        id="located_shot",
        user_id="u1",
        kind=ShotKind.PHOTO,
        filename="located.jpg",
        mime_type="image/jpeg",
        grid=GridSpec(cols=8, rows=6, width=800, height=600),
    )
    analysis = Analysis(
        shot_id=shot.id,
        user_id=shot.user_id,
        model="gemini-test",
        findings=[
            Finding(
                finding_id="off_guide_subject",
                what="The subject misses the selected placement line",
                why="The subject centre is 18% of frame width from the nearest line",
                cells=["B3", "C3"],
            )
        ],
    )
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(ctx.store, analysis)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": "u1"}
    try:
        with TestClient(main.app) as client:
            response = client.get(f"/api/shots/{shot.id}")
    finally:
        main.app.dependency_overrides.clear()

    receipt = response.json()["teaching"]
    assert receipt["primary_layer"] == "finding"
    assert receipt["notice_cells"] == ["B3", "C3"]
    assert "deliberately reject" in receipt["visible_check"]


async def test_uncertain_analysis_does_not_invent_a_lesson_or_image_layer():
    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    user = User(id="quiet_user", email="quiet@example.test")
    shot = Shot(
        id="quiet_shot",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        filename="quiet.jpg",
        mime_type="image/jpeg",
        status=ShotStatus.ANALYZED,
        grid=GridSpec(cols=8, rows=6, width=800, height=600),
    )
    await repo.put_user(ctx.store, user)
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=user.id,
            model="gemini-test",
            abstained="The panel did not reach independent agreement.",
        ),
    )
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            response = client.get(f"/api/shots/{shot.id}")
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    receipt = response.json()["teaching"]
    assert receipt["keep_title"] == ""
    assert receipt["notice_title"] == ""
    assert receipt["try_text"] == ""
    assert receipt["visible_check"] == ""
    assert receipt["primary_layer"] == "clean"


async def test_a_strong_read_does_not_turn_crop_salvage_into_homework():
    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    user = User(id="strong_user", email="strong@example.test")
    shot = Shot(
        id="strong_shot",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        filename="strong.jpg",
        mime_type="image/jpeg",
        grid=GridSpec(cols=8, rows=6, width=800, height=600),
    )
    await repo.put_user(ctx.store, user)
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="silhouette",
                    confidence=0.92,
                    agreement=2,
                    note="The subject reads as a clean dark shape against the sky.",
                )
            ],
            composition=Composition(
                guide="centre",
                moves=[
                    Move(
                        what="Raise exposure until the silhouette becomes a normal portrait",
                        kind=MoveKind.CAMERA,
                        reason="Replace the silhouette with visible facial detail.",
                        challenges_technique_ids=["silhouette"],
                    ),
                    Move(
                        what="Crop the subject off centre",
                        kind=MoveKind.CROP,
                        to_cells=["B1", "H6"],
                        reason="Make the placement follow a common guide.",
                    )
                ],
            ),
        ),
    )
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            response = client.get(f"/api/shots/{shot.id}")
    finally:
        main.app.dependency_overrides.clear()

    receipt = response.json()["teaching"]
    assert receipt["keep_technique_id"] == "silhouette"
    assert receipt["try_text"] == ""
    assert receipt["visible_check"] == ""
    assert receipt["primary_layer"] == "guide"
