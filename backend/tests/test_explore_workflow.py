"""Corrected Explore through real API, Store, Judge routing, and batch barriers."""

from datetime import timedelta

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    Analysis,
    Constraints,
    ExperimentStatus,
    RunStage,
    Shot,
    ShotKind,
    ShotSource,
    TechniqueEvidence,
    User,
    now,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.store import InMemoryStore
from app.services import judge, runs
from app.services.context import Context


def explore_context() -> Context:
    return Context(
        store=InMemoryStore(),
        blobs=None,
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )


async def test_explore_records_variations_without_criteria_or_verdicts():
    ctx = explore_context()
    user = User(
        id="explorer",
        email="explorer@example.test",
        constraints=Constraints(missing_gear=["tripod"]),
    )
    await repo.put_user(ctx.store, user)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {
        "id": user.id,
        "device_id": "android-device",
        "device": "Android",
    }
    try:
        with TestClient(main.app) as client:
            catalogue_response = client.get("/api/techniques/catalogue")
            assert catalogue_response.status_code == 200
            catalogue = catalogue_response.json()
            by_id = {item["technique_id"]: item for item in catalogue}
            assert by_id["negative_space"]["observed"] is False
            assert by_id["negative_space"]["description"].startswith("A small subject")
            assert "long_exposure" not in by_id
            assert all(item["family"] != "video" for item in catalogue)
            issued = client.post(
                "/api/experiments/explore?technique_id=negative_space"
            )
            assert issued.status_code == 200, issued.text
            experiment = issued.json()
            assert experiment["type"] == "explore"
            assert experiment["criteria"] == {"exif": _empty_exif(), "vision": [], "text": []}
            assert len(experiment["variations"]) == 3
            assert experiment["verdicts"] == []
            missing_variation = client.post(
                "/api/capture-sessions",
                json={"experiment_id": experiment["id"]},
            )
            assert missing_variation.status_code == 409
            variation_id = experiment["variations"][0]["id"]
            reserved = client.post(
                "/api/capture-sessions",
                json={
                    "experiment_id": experiment["id"],
                    "variation_id": variation_id,
                },
            )
            assert reserved.status_code == 201, reserved.text
            session_id = reserved.json()["id"]
            committed = client.put(
                f"/api/capture-sessions/{session_id}/manifest",
                json={
                    "members": [
                        {"source_id": "source-a", "order": 0},
                        {"source_id": "source-b", "order": 1},
                    ]
                },
            )
            assert committed.status_code == 200, committed.text

            first = await _member(ctx, user.id, experiment["id"], session_id, variation_id, "a")
            second = await _member(ctx, user.id, experiment["id"], session_id, variation_id, "b")
            await repo.accept_capture_session_member(ctx.store, session_id, "source-a", first.id)
            await repo.accept_capture_session_member(ctx.store, session_id, "source-b", second.id)
            await repo.put_analysis(
                ctx.store,
                Analysis(
                    shot_id=first.id,
                    user_id=user.id,
                    model="reader-v1",
                    prompt_version="prompt-v1",
                    techniques=[
                        TechniqueEvidence(
                            technique_id="negative_space",
                            confidence=0.9,
                            agreement=2,
                        )
                    ],
                ),
            )

            routed = await judge._judge(ctx, {"shot_id": first.id})
            assert routed == "Explore Variation observed; no Verdict"
            for stage in RunStage:
                await runs.completed(ctx, first.id, stage, f"{stage.value} complete")
            await runs.terminal(ctx, second.id, RunStage.INGEST, "unsupported media")

            detail = client.get(f"/api/capture-sessions/{session_id}")
            finished = client.post(f"/api/experiments/{experiment['id']}/complete")
    finally:
        main.app.dependency_overrides.clear()

    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "settled"
    assert detail.json()["variation_id"] == variation_id
    assert detail.json()["summary"]["observed"] == 1
    assert detail.json()["summary"]["terminal"] == 1
    assert detail.json()["verdicts"] == []
    stored = await repo.get_experiment(ctx.store, experiment["id"])
    assert stored.result_shot_ids == [first.id, second.id]
    assert [item.shot_id for item in stored.variation_observations] == [first.id]
    assert stored.variation_observations[0].variation_id == variation_id
    assert stored.variation_observations[0].corroborated_technique_ids == [
        "negative_space"
    ]
    assert stored.verdicts == []
    assert finished.status_code == 200, finished.text
    assert finished.json()["status"] == ExperimentStatus.COMPLETED.value
    assert finished.json()["verdicts"] == []
    stages = [event.stage for event in await repo.list_events(ctx.store, user.id)]
    assert stages.count("explore_session_evaluated") == 1
    assert stages.count("explore_completed") == 1
    assert not any(stage.startswith("criteria_") for stage in stages)


async def _member(
    ctx: Context,
    user_id: str,
    experiment_id: str,
    session_id: str,
    variation_id: str,
    suffix: str,
) -> Shot:
    shot = Shot(
        id=f"explore_{suffix}",
        user_id=user_id,
        kind=ShotKind.PHOTO,
        source=ShotSource.ANDROID,
        source_id=f"source-{suffix}",
        filename=f"{suffix}.jpg",
        mime_type="image/jpeg",
        experiment_id=experiment_id,
        variation_id=variation_id,
        capture_session_id=session_id,
        captured_at=now() + timedelta(seconds=1 if suffix == "b" else 0),
    )
    await repo.put_shot(ctx.store, shot)
    await runs.ensure(ctx, shot)
    return shot


def _empty_exif() -> dict[str, None]:
    return {
        "shutter_max_s": None,
        "shutter_min_s": None,
        "aperture_max": None,
        "aperture_min": None,
        "iso_min": None,
        "iso_max": None,
        "focal_min_mm": None,
        "focal_max_mm": None,
        "flash": None,
    }
