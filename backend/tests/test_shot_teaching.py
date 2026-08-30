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
    TechniqueState,
    TechniqueStatus,
    User,
    VisualPath,
    VisualPathRole,
    VisualRegion,
    VisualRegionRole,
    now,
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
                        what="Lower the camera below the bamboo pole",
                        kind=MoveKind.CAMERA,
                        reason="Keep the bamboo pole from crossing the subject.",
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
    assert response.json()["analysis"]["techniques"][0]["name"] == "Negative space"
    teaching = response.json()["teaching"]
    assert teaching["keep_technique_id"] == "negative_space"
    assert teaching["keep_title"] == "Negative space"
    assert teaching["keep_authority"] == "model_read"
    assert teaching["keep_mark"] == {
        "kind": "region",
        "cells": ["B2", "C2"],
        "to_cells": [],
        "paths": [],
        "regions": [],
        "visual_artifact": None,
        "technique_id": "negative_space",
        "finding_id": "",
    }
    assert "second sentence" not in teaching["keep_proof"]
    assert teaching["notice_finding_id"] == "camera_shake"
    assert teaching["notice_authority"] == "measured"
    assert teaching["notice_mark"]["kind"] == "finding"
    assert teaching["notice_mark"]["finding_id"] == "camera_shake"
    assert teaching["try_kind"] == "camera"
    assert teaching["try_text"] == "Lower the camera below the bamboo pole."
    assert teaching["try_mark"]["kind"] == "line"
    assert teaching["try_mark"]["cells"] == [f"{column}2" for column in "ABCDEFGH"]
    assert teaching["check_mark"] == teaching["try_mark"]
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
    assert receipt["notice_cells"] == [f"{column}2" for column in "ABCDEFGH"]
    assert receipt["notice_mark"]["kind"] == "line"
    assert receipt["try_mark"] == receipt["notice_mark"]


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
    assert receipt["notice_mark"]["kind"] == "finding"
    assert receipt["check_mark"] == receipt["notice_mark"]
    assert "Ignoring it can be a choice too" in receipt["visible_check"]


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
    assert receipt["keep_mark"]["kind"] == "none"
    assert receipt["notice_mark"]["kind"] == "none"
    assert receipt["try_mark"]["kind"] == "none"
    assert receipt["check_mark"]["kind"] == "none"


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

    receipt = response.json()["teaching"]
    assert receipt["keep_technique_id"] == "silhouette"
    assert receipt["try_text"] == ""
    assert receipt["visible_check"] == ""
    assert receipt["primary_layer"] == "guide"
    assert receipt["keep_mark"]["kind"] == "none"


async def test_every_visible_story_claim_carries_its_own_supported_mark():
    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    user = User(id="marks_user", email="marks@example.test")
    await repo.put_user(ctx.store, user)

    analyses = {
        "market": Analysis(
            shot_id="market",
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="leading_lines",
                    confidence=0.91,
                    agreement=2,
                    cells=["E6", "E7", "E8", "E9", "F6", "F7", "F8", "D5"],
                    paths=[
                        VisualPath(
                            points=["D9", "D7", "D5"],
                            leads_to=["D4", "E4"],
                            role=VisualPathRole.BOUNDARY,
                        ),
                        VisualPath(
                            points=["G9", "F7", "E5"],
                            leads_to=["D4", "E4"],
                            role=VisualPathRole.BOUNDARY,
                        ),
                    ],
                    note="The wet corridor draws the eye toward the subject.",
                )
            ],
            observations=[
                "A person with a red umbrella occupies cells D3 through E6.",
                "The teal tarp fills cells A5 through D9 in the foreground.",
            ],
            composition=Composition(
                moves=[
                    Move(
                        what="Step forward past the tarp",
                        kind=MoveKind.CAMERA,
                        reason="Reduce the teal tarp in the foreground.",
                    )
                ]
            ),
        ),
        "frame": Analysis(
            shot_id="frame",
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="frame_within_frame",
                    confidence=0.88,
                    agreement=2,
                    cells=["B2", "C2", "D2", "E2", "B3", "E3", "B4", "E4"],
                    note="The doorway encloses the subject.",
                )
            ],
        ),
        "pair": Analysis(
            shot_id="pair",
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="warm_cool",
                    confidence=0.9,
                    agreement=2,
                    cells=["A1", "B1", "G1", "H1"],
                    regions=[
                        VisualRegion(
                            cells=["A1", "B1"],
                            role=VisualRegionRole.WARM,
                            order=0,
                        ),
                        VisualRegion(
                            cells=["G1", "H1"],
                            role=VisualRegionRole.COOL,
                            order=1,
                        ),
                    ],
                    note="Warm light and cool shadow remain separate.",
                )
            ],
        ),
        "pair_missing": Analysis(
            shot_id="pair_missing",
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="warm_cool",
                    confidence=0.9,
                    agreement=2,
                    cells=["A1", "B1", "G1", "H1"],
                    note="Warm light and cool shadow remain separate.",
                )
            ],
        ),
        "planes": Analysis(
            shot_id="planes",
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="layering",
                    confidence=0.91,
                    agreement=2,
                    cells=["A6", "D5", "D3"],
                    regions=[
                        VisualRegion(
                            cells=["A6", "B6", "C6", "D6"],
                            role=VisualRegionRole.FOREGROUND,
                            order=0,
                        ),
                        VisualRegion(
                            cells=["C5", "D5", "E5", "F5"],
                            role=VisualRegionRole.MIDGROUND,
                            order=1,
                        ),
                        VisualRegion(
                            cells=["C3", "D3", "E3", "F3"],
                            role=VisualRegionRole.BACKGROUND,
                            order=2,
                        ),
                    ],
                    note="Foreground, cloud, and ridge form three depth planes.",
                )
            ],
        ),
        "planes_missing": Analysis(
            shot_id="planes_missing",
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="layering",
                    confidence=0.91,
                    agreement=2,
                    cells=["A6", "D5", "D3"],
                    note="Foreground, cloud, and ridge form three depth planes.",
                )
            ],
        ),
        "instances_missing": Analysis(
            shot_id="instances_missing",
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="patterns",
                    confidence=0.88,
                    agreement=2,
                    cells=["B2", "D2", "F2"],
                    note="Three windows repeat across the wall.",
                )
            ],
        ),
        "move": Analysis(
            shot_id="move",
            user_id=user.id,
            model="gemini-test",
            observations=["The cup occupies cell B4 beside the frame edge."],
            composition=Composition(
                moves=[
                    Move(
                        what="Move the cup right",
                        kind=MoveKind.MOVE,
                        from_cells=["B4"],
                        to_cells=["D4"],
                        reason="Separate it from the edge.",
                    )
                ]
            ),
        ),
        "crop": Analysis(
            shot_id="crop",
            user_id=user.id,
            model="gemini-test",
            observations=["A shelf fills cells A1 through B6."],
            composition=Composition(
                moves=[
                    Move(
                        what="Crop past the shelf",
                        kind=MoveKind.CROP,
                        to_cells=["C1", "H6"],
                        reason="Remove the shelf.",
                    )
                ]
            ),
        ),
    }
    for shot_id, analysis in analyses.items():
        await repo.put_shot(
            ctx.store,
            Shot(
                id=shot_id,
                user_id=user.id,
                kind=ShotKind.PHOTO,
                filename=f"{shot_id}.jpg",
                mime_type="image/jpeg",
                status=ShotStatus.ANALYZED,
                grid=GridSpec(cols=8, rows=9, width=800, height=900),
            ),
        )
        await repo.put_analysis(ctx.store, analysis)

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            receipts = {
                shot_id: client.get(f"/api/shots/{shot_id}").json()["teaching"]
                for shot_id in analyses
            }
    finally:
        main.app.dependency_overrides.clear()

    assert receipts["market"]["keep_mark"]["kind"] == "line"
    assert [path["points"] for path in receipts["market"]["keep_mark"]["paths"]] == [
        ["D9", "D7", "D5"],
        ["G9", "F7", "E5"],
    ]
    assert receipts["market"]["notice_mark"]["kind"] == "region"
    assert receipts["market"]["notice_mark"]["cells"] == [
        f"{column}{row}" for row in range(5, 10) for column in "ABCD"
    ]
    assert receipts["market"]["try_mark"] == receipts["market"]["notice_mark"]
    assert receipts["market"]["check_mark"] == receipts["market"]["notice_mark"]
    assert receipts["frame"]["keep_mark"]["kind"] == "frame"
    assert receipts["pair"]["keep_mark"]["kind"] == "pair"
    assert [region["role"] for region in receipts["pair"]["keep_mark"]["regions"]] == [
        "warm",
        "cool",
    ]
    assert receipts["pair_missing"]["keep_mark"]["kind"] == "pair"
    assert receipts["pair_missing"]["keep_mark"]["regions"] == []
    assert receipts["planes"]["keep_mark"]["kind"] == "planes"
    assert [region["role"] for region in receipts["planes"]["keep_mark"]["regions"]] == [
        "foreground",
        "midground",
        "background",
    ]
    assert receipts["planes_missing"]["keep_mark"]["kind"] == "planes"
    assert receipts["planes_missing"]["keep_mark"]["regions"] == []
    assert receipts["instances_missing"]["keep_mark"]["kind"] == "instances"
    assert receipts["instances_missing"]["keep_mark"]["regions"] == []
    assert receipts["move"]["try_mark"]["kind"] == "move"
    assert receipts["move"]["try_mark"]["cells"] == ["B4"]
    assert receipts["move"]["try_mark"]["to_cells"] == ["D4"]
    assert receipts["crop"]["try_mark"]["kind"] == "crop"
    assert receipts["crop"]["try_mark"]["cells"] == ["C1", "H6"]


async def test_shot_detail_places_current_technique_map_context_beside_exact_evidence():
    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    user = User(id="context_user", email="context@example.test")
    shot = Shot(
        id="context_shot",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        filename="context.jpg",
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
                    technique_id="leading_lines",
                    confidence=0.91,
                    agreement=2,
                    cells=["D6", "D4", "D2"],
                ),
                TechniqueEvidence(
                    technique_id="complementary",
                    confidence=0.95,
                    agreement=1,
                    cells=["A1", "H6"],
                ),
            ],
        ),
    )
    await repo.put_technique_state(
        ctx.store,
        TechniqueState(
            user_id=user.id,
            technique_id="leading_lines",
            status=TechniqueStatus.RECURRING,
            attempts=8,
            corroborated=6,
            sightings=8,
            corroborated_shots=6,
            distinct_scenes=4,
            distinct_shoots=3,
            reproduce_sessions=2,
            evaluable_reproduce_sessions=2,
            criteria_met_sessions=1,
            positive_keeper_shots=2,
        ),
    )
    await repo.put_technique_state(
        ctx.store,
        TechniqueState(
            user_id=user.id,
            technique_id="complementary",
            status=TechniqueStatus.OBSERVED,
            attempts=1,
            sightings=1,
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
    assert response.json()["technique_context"] == {
        "leading_lines": {
            "technique_id": "leading_lines",
            "status": "recurring",
            "corroborated_shots": 6,
            "distinct_scenes": 4,
            "distinct_shoots": 3,
            "reproduce_sessions": 2,
            "evaluable_reproduce_sessions": 2,
            "criteria_met_sessions": 1,
            "positive_keeper_shots": 2,
        }
    }


async def test_targeted_reproduce_does_not_substitute_another_keeper_technique():
    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    user = User(id="target_user", email="target@example.test")
    keeper = Shot(
        id="target_keeper",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        filename="keeper.jpg",
        mime_type="image/jpeg",
        status=ShotStatus.ANALYZED,
        kept_at=now(),
        grid=GridSpec(cols=8, rows=6, width=800, height=600),
    )
    await repo.put_user(ctx.store, user)
    await repo.put_shot(ctx.store, keeper)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=keeper.id,
            user_id=user.id,
            model="gemini-test",
            techniques=[
                TechniqueEvidence(
                    technique_id="negative_space",
                    confidence=0.9,
                    agreement=2,
                )
            ],
        ),
    )

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/api/experiments/issue",
                params={"technique_id": "leading_lines"},
            )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() is None
    assert await repo.open_experiment(ctx.store, user.id) is None
