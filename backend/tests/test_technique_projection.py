"""Technique Map projection through real Store and Cartographer seams."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    Analysis,
    CaptureMemberOutcome,
    CaptureSession,
    CaptureSessionMember,
    CaptureSessionStatus,
    Criteria,
    Experiment,
    ExperimentStatus,
    ExperimentType,
    Scene,
    Shoot,
    Shot,
    ShotKind,
    TechniqueEvidence,
    TechniqueStatus,
    User,
    Verdict,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.store import InMemoryStore
from app.services import cartographer
from app.services.context import Context


def context() -> Context:
    return Context(
        store=InMemoryStore(),
        blobs=None,
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )


async def add_shot(
    ctx: Context,
    shot_id: str,
    at: datetime,
    *,
    agreement: int = 2,
    keeper: bool = False,
) -> Shot:
    shot = Shot(
        id=shot_id,
        user_id="projection_user",
        kind=ShotKind.PHOTO,
        filename=f"{shot_id}.jpg",
        mime_type="image/jpeg",
        captured_at=at,
        kept_at=at if keeper else None,
    )
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=shot.user_id,
            model="reader-v1",
            prompt_version="prompt-v1",
            techniques=[
                TechniqueEvidence(
                    technique_id="panning",
                    confidence=0.9,
                    agreement=agreement,
                )
            ],
        ),
    )
    return shot


async def test_rebuild_keeps_each_evidence_axis_separate_and_exposes_it():
    ctx = context()
    user = User(id="projection_user", email="projection@example.test")
    await repo.put_user(ctx.store, user)
    start = datetime(2026, 8, 27, 8, 0, tzinfo=UTC)
    first = await add_shot(ctx, "shot_1", start, keeper=True)
    second = await add_shot(ctx, "shot_2", start + timedelta(minutes=1), keeper=True)
    third = await add_shot(ctx, "shot_3", start + timedelta(minutes=8))
    weak = await add_shot(ctx, "shot_4", start + timedelta(hours=2), agreement=1)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=first.id,
            user_id=user.id,
            model="reader-v1",
            prompt_version="prompt-v1",
            techniques=[
                TechniqueEvidence(technique_id="panning", confidence=0.65, agreement=1),
                TechniqueEvidence(technique_id="panning", confidence=0.9, agreement=2),
            ],
        ),
    )
    shoot_a = Shoot(
        id="shoot_a",
        user_id=user.id,
        ordered_scene_ids=["scene_a", "scene_b"],
        ordered_shot_ids=[first.id, second.id, third.id],
    )
    shoot_b = Shoot(
        id="shoot_b",
        user_id=user.id,
        ordered_scene_ids=["scene_c"],
        ordered_shot_ids=[weak.id],
    )
    await repo.put_shoot(ctx.store, shoot_a)
    await repo.put_shoot(ctx.store, shoot_b)
    for scene in (
        Scene(
            id="scene_a",
            user_id=user.id,
            shoot_id=shoot_a.id,
            ordered_shot_ids=[first.id, second.id],
        ),
        Scene(
            id="scene_b",
            user_id=user.id,
            shoot_id=shoot_a.id,
            ordered_shot_ids=[third.id],
        ),
        Scene(
            id="scene_c",
            user_id=user.id,
            shoot_id=shoot_b.id,
            ordered_shot_ids=[weak.id],
        ),
    ):
        await repo.put_scene(ctx.store, scene)
    experiment = Experiment(
        id="experiment_panning",
        user_id=user.id,
        technique_id="panning",
        type=ExperimentType.REPRODUCE,
        title="Repeat panning",
        brief="Repeat the motion.",
        why_now="Keeper evidence",
        criteria=Criteria(vision=["panning"]),
        reference_shot_id=first.id,
        result_shot_ids=[first.id, third.id, weak.id],
        verdicts=[
            Verdict(
                shot_id=first.id,
                criteria_met=True,
                feedback="The declared motion appeared.",
            )
        ],
        status=ExperimentStatus.COMPLETED,
    )
    await repo.put_experiment(ctx.store, experiment)
    session = CaptureSession(
        id="capture_panning",
        user_id=user.id,
        experiment_id=experiment.id,
        device_id="device",
        expires_at=start + timedelta(hours=3),
    )
    assert await repo.create_capture_session(ctx.store, session)
    await repo.commit_capture_session(
        ctx.store,
        session.id,
        [
            CaptureSessionMember(
                source_id="camera:first",
                order=0,
                shot_id=first.id,
                outcome=CaptureMemberOutcome.CRITERIA_MET,
            ),
            CaptureSessionMember(
                source_id="camera:third",
                order=1,
                shot_id=third.id,
                outcome=CaptureMemberOutcome.CRITERIA_NOT_MET,
            ),
            CaptureSessionMember(
                source_id="camera:weak",
                order=2,
                shot_id=weak.id,
                outcome=CaptureMemberOutcome.ABSTAINED,
            ),
        ],
        start,
    )
    settled_session = (await repo.get_capture_session(ctx.store, session.id)).model_copy(
        update={"status": CaptureSessionStatus.SETTLED, "settled_at": start}
    )
    await ctx.store.put(
        repo.CAPTURE_SESSIONS,
        settled_session.id,
        settled_session.model_dump(mode="json"),
    )
    retry_experiment = Experiment(
        id="experiment_panning_retry",
        user_id=user.id,
        technique_id="panning",
        type=ExperimentType.REPRODUCE,
        title="Repeat panning again",
        brief="Repeat the motion in another Camera visit.",
        why_now="Test the same decision again.",
        criteria=Criteria(vision=["panning"]),
        reference_shot_id=first.id,
    )
    await repo.put_experiment(ctx.store, retry_experiment)
    terminal_session = CaptureSession(
        id="capture_panning_terminal",
        user_id=user.id,
        experiment_id=retry_experiment.id,
        device_id="device",
        status=CaptureSessionStatus.SETTLED,
        members=[
            CaptureSessionMember(
                source_id="camera:terminal",
                order=0,
                outcome=CaptureMemberOutcome.TERMINAL,
            )
        ],
        expires_at=start + timedelta(hours=4),
        settled_at=start + timedelta(hours=1),
    )
    await ctx.store.put(
        repo.CAPTURE_SESSIONS,
        terminal_session.id,
        terminal_session.model_dump(mode="json"),
    )

    rebuilt = await cartographer.rebuild(ctx, user.id)
    state = rebuilt["panning"]

    assert state.status is TechniqueStatus.RECURRING
    assert state.sightings == state.attempts == 4
    assert state.corroborated_shots == state.corroborated == 3
    assert state.distinct_scenes == 2
    assert state.distinct_shoots == 1
    assert state.reproduce_attempts == 3
    assert state.criteria_met_results == 1
    assert state.reproduce_sessions == 2
    assert state.evaluable_reproduce_sessions == 1
    assert state.criteria_met_sessions == 1
    assert state.abstentions == 1
    assert state.positive_keeper_shots == 2
    assert state.supported_condition_coverage == {}
    assert state.projection_version == "technique-map-4"
    assert len(state.input_digest) == 16
    assert "score" not in state.model_dump()

    replay = await cartographer.rebuild(ctx, user.id)
    assert replay["panning"].model_dump(exclude={"last_observed"}) == state.model_dump(
        exclude={"last_observed"}
    )

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            response = client.get("/api/techniques")
            assert response.status_code == 200, response.text
            node = response.json()[0]
    finally:
        main.app.dependency_overrides.clear()
    assert node["sightings"] == 4
    assert node["corroborated_shots"] == 3
    assert node["distinct_scenes"] == 2
    assert node["distinct_shoots"] == 1
    assert node["reproduce_attempts"] == 3
    assert node["criteria_met_results"] == 1
    assert node["reproduce_sessions"] == 2
    assert node["evaluable_reproduce_sessions"] == 1
    assert node["criteria_met_sessions"] == 1
    assert node["abstentions"] == 1
    assert node["positive_keeper_shots"] == 2
    assert "score" not in node


async def test_rebuild_retracts_a_projection_when_its_analysis_no_longer_supports_it():
    ctx = context()
    user = User(id="projection_user", email="projection@example.test")
    await repo.put_user(ctx.store, user)
    shot = await add_shot(
        ctx,
        "retracted_shot",
        datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
        keeper=True,
    )
    first = await cartographer.rebuild(ctx, user.id)
    original_digest = first["panning"].input_digest
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=user.id,
            model="reader-v2",
            prompt_version="prompt-v2",
            techniques=[],
        ),
    )

    rebuilt = await cartographer.rebuild(ctx, user.id)
    retracted = rebuilt["panning"]

    assert retracted.status is TechniqueStatus.UNOBSERVED
    assert retracted.sightings == retracted.attempts == 0
    assert retracted.corroborated_shots == retracted.corroborated == 0
    assert retracted.positive_keeper_shots == 0
    assert retracted.input_digest != original_digest


async def test_experiment_history_remains_visible_after_current_sightings_retract():
    ctx = context()
    user = User(id="projection_user", email="projection@example.test")
    await repo.put_user(ctx.store, user)
    at = datetime(2026, 8, 27, 12, 30, tzinfo=UTC)
    shot = await add_shot(ctx, "historical_result", at)
    await repo.put_experiment(
        ctx.store,
        Experiment(
            id="historical_reproduce",
            user_id=user.id,
            technique_id="panning",
            type=ExperimentType.REPRODUCE,
            title="Repeat panning",
            brief="Repeat the motion.",
            why_now="Earlier Evidence",
            criteria=Criteria(vision=["panning"]),
            result_shot_ids=[shot.id],
            status=ExperimentStatus.COMPLETED,
        ),
    )
    await cartographer.rebuild(ctx, user.id)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id=shot.id,
            user_id=user.id,
            model="reader-v2",
            prompt_version="prompt-v2",
            techniques=[],
        ),
    )
    rebuilt = await cartographer.rebuild(ctx, user.id)
    assert rebuilt["panning"].status is TechniqueStatus.UNOBSERVED
    assert rebuilt["panning"].sightings == 0
    assert rebuilt["panning"].reproduce_attempts == 1

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            response = client.get("/api/techniques")
            assert response.status_code == 200, response.text
    finally:
        main.app.dependency_overrides.clear()
    assert response.json() == [
        {
            "technique_id": "panning",
            "name": "Panning",
            "family": "exposure",
            "status": "unobserved",
            "attempts": 0,
            "corroborated": 0,
            "sightings": 0,
            "corroborated_shots": 0,
            "distinct_scenes": 0,
            "distinct_shoots": 0,
            "reproduce_attempts": 1,
            "criteria_met_results": 0,
            "reproduce_sessions": 0,
            "evaluable_reproduce_sessions": 0,
            "criteria_met_sessions": 0,
            "abstentions": 0,
            "positive_keeper_shots": 0,
            "supported_condition_coverage": {},
            "projection_version": "technique-map-4",
            "input_digest": rebuilt["panning"].input_digest,
            "last_observed": None,
        }
    ]


async def test_keeper_removal_rebuilds_positive_evidence_without_creating_dislike():
    ctx = context()
    user = User(id="projection_user", email="projection@example.test")
    await repo.put_user(ctx.store, user)
    shot = await add_shot(
        ctx,
        "keeper_signal",
        datetime(2026, 8, 27, 13, 0, tzinfo=UTC),
        keeper=True,
    )
    initial = await cartographer.rebuild(ctx, user.id)
    assert initial["panning"].positive_keeper_shots == 1
    deps.wire(ctx)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            response = client.put(f"/api/shots/{shot.id}/keeper", json={"keeper": False})
            assert response.status_code == 200, response.text
        await ctx.bus.drain()
    finally:
        main.app.dependency_overrides.clear()

    rebuilt = {
        item.technique_id: item for item in await repo.list_technique_states(ctx.store, user.id)
    }
    assert rebuilt["panning"].positive_keeper_shots == 0
    assert rebuilt["panning"].sightings == 1
    assert rebuilt["panning"].corroborated_shots == 1
    assert (await repo.get_shot(ctx.store, shot.id)).kept_at is None
