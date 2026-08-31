"""Camera capability and corrected Criteria behavior across HTTP and the real store."""

import pytest
from fastapi.testclient import TestClient

from app.agents import scout
from app.api import deps, main
from app.api.auth import current_user
from app.domain import experiment_criteria, taxonomy
from app.domain.entities import (
    Analysis,
    Criteria,
    Exif,
    ExifRule,
    Experiment,
    ExperimentType,
    Shot,
    ShotKind,
    TechniqueEvidence,
    User,
    Verdict,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import judge as judge_service
from app.services import photographer_memory
from app.services.context import Context


async def test_fixed_aperture_report_changes_context_and_retires_legacy_capture(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "phone-photographer"
    device_id = "device-fixed-lens"
    await repo.put_user(ctx.store, User(id=user_id, email="camera@example.test"))
    await repo.put_device(ctx.store, device_id, user_id, "Xiaomi 14T")
    legacy = Experiment(
        id="legacy-deep-dof",
        user_id=user_id,
        technique_id="deep_dof",
        type=ExperimentType.REPRODUCE,
        title="Hold sharpness front to back",
        brief="Use f/8.",
        why_now="A Keeper supported the visible goal.",
        criteria=Criteria(
            exif=ExifRule(aperture_min=8.0),
            vision=["deep_dof"],
            text=["Use f/8", "Keep nearby and distant detail sharp"],
        ),
    )
    assert await repo.create_open_experiment(ctx.store, legacy)

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {
        "id": user_id,
        "device": "Xiaomi 14T",
        "device_id": device_id,
    }
    try:
        with TestClient(main.app) as client:
            reported = client.put(
                "/api/devices/current/camera-capabilities",
                json={
                    "manufacturer": "Xiaomi",
                    "model": "2306EPN60G",
                    "cameras": [
                        {"camera_id": "0", "facing": "back", "apertures": [1.7]},
                        {"camera_id": "1", "facing": "front", "apertures": None},
                    ],
                },
            )
            assert reported.status_code == 204, reported.text

            snapshot = client.get("/api/mobile/snapshot")
            assert snapshot.status_code == 200, snapshot.text
            assert "camera_capabilities" in snapshot.json()["capabilities"]
            assert (
                "Earlier results are kept unchanged"
                in snapshot.json()["open_experiment"]["criteria_notice"]
            )

            blocked = client.post("/api/capture-sessions", json={"experiment_id": legacy.id})
            assert blocked.status_code == 409, blocked.text
            assert "unsuitable check" in blocked.json()["detail"]

        constraints = await photographer_memory.constraints_for(
            ctx, user_id, role="scout", purpose="experiment_selection"
        )
        assert constraints.camera_reports[0].cameras[0].apertures == [1.7]

        corrected = scout.criteria_for(taxonomy.BY_ID["deep_dof"], ["Use f/8"])
        assert corrected.exif.aperture_min is None
        assert corrected.text == ["Nearby and distant detail are both visibly sharp."]
    finally:
        main.app.dependency_overrides.clear()


@pytest.mark.parametrize("apertures", [[1.7], [2.8, 4.0, 8.0], None])
async def test_reported_controls_stay_scoped_and_do_not_change_visual_goal(tmp_path, apertures):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    await repo.put_user(ctx.store, User(id="owner", email="owner@example.test"))
    await repo.put_user(ctx.store, User(id="other", email="other@example.test"))
    await repo.put_device(ctx.store, "owned-device", "owner", "camera")
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {
        "id": "owner",
        "device_id": "owned-device",
    }
    try:
        with TestClient(main.app) as client:
            payload = {"cameras": [{"camera_id": "0", "apertures": apertures}]}
            for _ in range(2):
                response = client.put("/api/devices/current/camera-capabilities", json=payload)
                assert response.status_code == 204, response.text
            invalid = client.put(
                "/api/devices/current/camera-capabilities",
                json={"cameras": [{"camera_id": "0", "apertures": [-8.0]}]},
            )
            assert invalid.status_code == 422
        own = await photographer_memory.constraints_for(ctx, "owner", role="scout", purpose="test")
        other = await photographer_memory.constraints_for(
            ctx, "other", role="scout", purpose="test"
        )
        assert own.camera_reports[0].cameras[0].apertures == apertures
        assert other.camera_reports == []
        for technique_id in experiment_criteria.VISUAL_GOALS:
            criteria = scout.criteria_for(taxonomy.BY_ID[technique_id], [])
            assert criteria.exif.model_dump(exclude_none=True) == {}
            assert criteria.vision == [technique_id]
        # A real setting-based goal retains its hard check.
        assert (
            scout.criteria_for(taxonomy.BY_ID["long_exposure"], []).exif.shutter_min_s is not None
        )
    finally:
        main.app.dependency_overrides.clear()


@pytest.mark.parametrize("legacy", [True, False])
async def test_judge_accounts_for_unsettled_focus_without_inventing_failure(tmp_path, legacy):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    await repo.put_user(ctx.store, User(id="owner", email="owner@example.test"))
    old_verdict = Verdict(shot_id="earlier", criteria_met=False, feedback="Historical feedback")
    experiment = Experiment(
        id="focus",
        user_id="owner",
        technique_id="deep_dof",
        type=ExperimentType.REPRODUCE,
        title="Near and far",
        brief="Keep both readable",
        why_now="A Keeper supported it",
        criteria=(
            Criteria(exif=ExifRule(aperture_min=8.0), vision=["deep_dof"])
            if legacy
            else scout.criteria_for(taxonomy.BY_ID["deep_dof"], [])
        ),
        verdicts=[old_verdict] if legacy else [],
        result_shot_ids=["earlier"] if legacy else [],
    )
    await repo.create_open_experiment(ctx.store, experiment)
    shot = Shot(
        id="next",
        user_id="owner",
        kind=ShotKind.PHOTO,
        filename="next.jpg",
        mime_type="image/jpeg",
        experiment_id=experiment.id,
        exif=Exif(f_number=1.7),
    )
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id="owner",
            model="stored-analysis-fixture",
            techniques=[TechniqueEvidence(technique_id="deep_dof", confidence=0.3)],
        ),
    )
    for _ in range(2):
        await judge_service.judge(ctx, {"shot_id": shot.id})
    saved = await repo.get_experiment(ctx.store, experiment.id)
    assert saved.verdicts == experiment.verdicts
    assert saved.criteria == experiment.criteria
    assert saved.result_shot_ids.count(shot.id) == 1
    assert saved.status.value == "open"
    events = await repo.list_events(ctx.store, "owner")
    abstentions = [event for event in events if event.stage == "abstained"]
    assert len(abstentions) == 1
    assert (
        "unsuitable" in abstentions[0].detail["reason"]
        if legacy
        else "visual Evidence" in abstentions[0].detail["reason"]
    )


async def test_scribe_redelivery_preserves_existing_legacy_review_bytes(tmp_path):
    from app.services import scribe
    from tests.test_scribe import seed

    ctx = await seed(str(tmp_path), with_verdict=True)
    experiment = await repo.get_experiment(ctx.store, "experiment_1")
    experiment.type = ExperimentType.REPRODUCE
    experiment.technique_id = "deep_dof"
    experiment.criteria = Criteria(exif=ExifRule(aperture_min=8.0), vision=["deep_dof"])
    await repo.put_experiment(ctx.store, experiment)
    publisher = scribe.LocalReviewPublisher(str(tmp_path))
    file_id = await scribe.write_review(ctx, {"shot_id": "shot_1"}, publisher)
    image = tmp_path / file_id
    caption = image.with_suffix(".txt")
    before = (image.read_bytes(), caption.read_bytes())
    assert b"Criteria correction" in before[1]
    assert b"Original feedback, kept for history" in before[1]

    analysis = await repo.find_analysis(ctx.store, "shot_1")
    analysis.critique = "A later reading must not silently replace this historical export."
    await repo.put_analysis(ctx.store, analysis)
    assert await scribe.write_review(ctx, {"shot_id": "shot_1"}, publisher) == file_id
    assert (image.read_bytes(), caption.read_bytes()) == before
    assert (await repo.list_events(ctx.store, "u1"))[0].stage == "review_preserved"
