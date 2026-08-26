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
