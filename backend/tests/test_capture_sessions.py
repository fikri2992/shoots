"""Capture Session behavior through HTTP, Store, blob, and ingress seams."""

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    Analysis,
    Baseline,
    CaptureSession,
    CaptureSessionMember,
    Criteria,
    Experiment,
    ExperimentStatus,
    ExperimentType,
    GridSpec,
    Provenance,
    RunStage,
    Shot,
    ShotKind,
    ShotSource,
    User,
    Verdict,
    now,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import capture_sessions as capture_session_service
from app.services import runs, scout
from app.services.context import Context
from tests.fixtures import jpeg_with_exif


async def test_committed_capture_session_owns_ingress_membership(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "u-capture"
    await repo.put_user(ctx.store, User(id=user_id, email="capture@example.test"))
    experiment = Experiment(
        id="experiment_capture",
        user_id=user_id,
        technique_id="rule_of_thirds",
        type=ExperimentType.REPRODUCE,
        title="Repeat the placement",
        brief="Put the subject on a thirds point.",
        why_now="A marked Keeper supports it.",
        criteria=Criteria(vision=["rule_of_thirds"], text=["Subject uses the thirds guide"]),
        reference_shot_id="keeper_1",
    )
    assert await repo.create_open_experiment(ctx.store, experiment)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {
        "id": user_id,
        "device": "Xiaomi 14T",
        "device_id": "device-1",
    }

    try:
        with TestClient(main.app) as client:
            reserved = client.post(
                "/api/capture-sessions",
                json={"experiment_id": experiment.id},
            )
            assert reserved.status_code == 201, reserved.text
            session_id = reserved.json()["id"]
            assert reserved.json()["status"] == "reserved"

            committed = client.put(
                f"/api/capture-sessions/{session_id}/manifest",
                json={
                    "members": [
                        {"source_id": "camera:101", "order": 0},
                        {"source_id": "camera:102", "order": 1},
                    ]
                },
            )
            assert committed.status_code == 200, committed.text
            assert committed.json()["status"] == "committed"
            identical = client.put(
                f"/api/capture-sessions/{session_id}/manifest",
                json={
                    "members": [
                        {"source_id": "camera:101", "order": 0},
                        {"source_id": "camera:102", "order": 1},
                    ]
                },
            )
            assert identical.status_code == 200, identical.text
            different = client.put(
                f"/api/capture-sessions/{session_id}/manifest",
                json={"members": [{"source_id": "camera:other", "order": 0}]},
            )
            assert different.status_code == 409, different.text

            first = client.post(
                "/api/ingress/shots",
                files={"file": ("IMG_101.jpg", jpeg_with_exif(), "image/jpeg")},
                data={
                    "source_id": "camera:101",
                    "capture_session_id": session_id,
                    "experiment_id": "client-must-not-win",
                },
            )
            assert first.status_code == 200, first.text
            assert first.json()["capture_session_id"] == session_id
            assert first.json()["experiment_id"] == experiment.id

            duplicate = client.post(
                "/api/ingress/shots",
                files={"file": ("IMG_101.jpg", jpeg_with_exif(), "image/jpeg")},
                data={"source_id": "camera:101", "capture_session_id": session_id},
            )
            assert duplicate.status_code == 200, duplicate.text
            assert duplicate.json()["created"] is False

            detail = client.get(f"/api/capture-sessions/{session_id}")
            assert detail.status_code == 200, detail.text
            assert [item["source_id"] for item in detail.json()["members"]] == [
                "camera:101",
                "camera:102",
            ]
            assert [item["id"] for item in detail.json()["shots"]] == [first.json()["shot_id"]]
            assert [item["shot_id"] for item in detail.json()["runs"]] == [first.json()["shot_id"]]

            foreign = client.post(
                "/api/ingress/shots",
                files={"file": ("IMG_999.jpg", jpeg_with_exif(), "image/jpeg")},
                data={"source_id": "camera:999", "capture_session_id": session_id},
            )
            assert foreign.status_code == 409, foreign.text
    finally:
        main.app.dependency_overrides.clear()

    stored = (await repo.list_shots(ctx.store, user_id))[0]
    assert stored.source is ShotSource.ANDROID
    assert stored.experiment_id == experiment.id
    assert stored.capture_session_id == session_id


async def test_only_one_capture_session_can_reserve_an_experiment(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "u-one-session"
    await repo.put_user(ctx.store, User(id=user_id, email="one@example.test"))
    experiment = Experiment(
        id="experiment_one_session",
        user_id=user_id,
        technique_id="low_key",
        type=ExperimentType.REPRODUCE,
        title="Repeat low key",
        brief="Keep most of the frame dark.",
        why_now="A marked Keeper supports it.",
        criteria=Criteria(vision=["low_key"], text=["The frame reads as low key"]),
        reference_shot_id="keeper_1",
    )
    assert await repo.create_open_experiment(ctx.store, experiment)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    device = {"id": "device-1"}
    main.app.dependency_overrides[current_user] = lambda: {
        "id": user_id,
        "device": "Xiaomi 14T",
        "device_id": device["id"],
    }

    try:
        with TestClient(main.app) as client:
            first = client.post("/api/capture-sessions", json={"experiment_id": experiment.id})
            same_device_retry = client.post(
                "/api/capture-sessions", json={"experiment_id": experiment.id}
            )
            device["id"] = "device-2"
            second = client.post("/api/capture-sessions", json={"experiment_id": experiment.id})
            cancelled = client.post(f"/api/capture-sessions/{first.json()['id']}/cancel")
            third = client.post("/api/capture-sessions", json={"experiment_id": experiment.id})
    finally:
        main.app.dependency_overrides.clear()

    assert first.status_code == 201, first.text
    assert same_device_retry.status_code == 201, same_device_retry.text
    assert same_device_retry.json()["id"] == first.json()["id"]
    assert second.status_code == 409, second.text
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    assert third.status_code == 201, third.text


async def test_abandoned_reservation_expires_and_releases_the_experiment(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "u-expired-capture"
    await repo.put_user(ctx.store, User(id=user_id, email="expired@example.test"))
    session = CaptureSession(
        id="capture_expired",
        user_id=user_id,
        experiment_id="experiment_expired",
        device_id="device-1",
        expires_at=now(),
    )
    assert await repo.create_capture_session(ctx.store, session)

    assert await capture_session_service.expire_reserved(ctx, user_id) == 1
    stored = await repo.get_capture_session(ctx.store, session.id)
    assert stored.status.value == "expired"
    assert await repo.active_capture_session(ctx.store, session.experiment_id) is None
    assert await capture_session_service.expire_reserved(ctx, user_id) == 0


async def test_reproduce_batch_records_every_result_before_it_completes(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "u-batch"
    await repo.put_user(ctx.store, User(id=user_id, email="batch@example.test"))
    experiment = Experiment(
        id="experiment_batch",
        user_id=user_id,
        technique_id="low_key",
        type=ExperimentType.REPRODUCE,
        title="Repeat low key",
        brief="Keep most of the frame dark.",
        why_now="A marked Keeper supports it.",
        criteria=Criteria(vision=["low_key"], text=["The frame reads as low key"]),
        reference_shot_id="keeper_1",
    )
    assert await repo.create_open_experiment(ctx.store, experiment)
    at = now()
    session = CaptureSession(
        id="capture_batch",
        user_id=user_id,
        experiment_id=experiment.id,
        device_id="device-1",
        expires_at=at,
    )
    assert await repo.create_capture_session(ctx.store, session)
    session, _ = await repo.commit_capture_session(
        ctx.store,
        session.id,
        [
            CaptureSessionMember(source_id="camera:1", order=0, shot_id="shot_1"),
            CaptureSessionMember(source_id="camera:2", order=1, shot_id="shot_2"),
            CaptureSessionMember(source_id="camera:3", order=2, shot_id="shot_3"),
        ],
        at,
    )

    await capture_session_service.record_judge_outcome(
        ctx,
        session.id,
        "shot_2",
        Verdict(shot_id="shot_2", criteria_met=True, feedback="Criteria met."),
    )
    assert (await repo.get_experiment(ctx.store, experiment.id)).status is ExperimentStatus.OPEN

    await capture_session_service.record_judge_outcome(
        ctx,
        session.id,
        "shot_1",
        Verdict(shot_id="shot_1", criteria_met=False, feedback="Not yet."),
    )
    assert (await repo.get_experiment(ctx.store, experiment.id)).status is ExperimentStatus.OPEN

    await capture_session_service.record_judge_outcome(
        ctx,
        session.id,
        "shot_3",
        None,
        abstained=True,
    )

    stored = await repo.get_experiment(ctx.store, experiment.id)
    assert stored.status is ExperimentStatus.COMPLETED
    assert stored.result_shot_ids == ["shot_1", "shot_2", "shot_3"]
    assert [verdict.shot_id for verdict in stored.verdicts] == ["shot_1", "shot_2"]
    evaluated = await repo.get_capture_session(ctx.store, session.id)
    assert evaluated.evaluated_at is not None
    assert evaluated.representative_result_shot_id == "shot_2"


async def test_batch_without_met_criteria_leaves_reproduce_open(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "u-batch-open"
    await repo.put_user(ctx.store, User(id=user_id, email="open@example.test"))
    experiment = Experiment(
        id="experiment_batch_open",
        user_id=user_id,
        technique_id="low_key",
        type=ExperimentType.REPRODUCE,
        title="Repeat low key",
        brief="Keep most of the frame dark.",
        why_now="A marked Keeper supports it.",
        criteria=Criteria(vision=["low_key"], text=["The frame reads as low key"]),
        reference_shot_id="keeper_1",
    )
    assert await repo.create_open_experiment(ctx.store, experiment)
    at = now()
    session = CaptureSession(
        id="capture_batch_open",
        user_id=user_id,
        experiment_id=experiment.id,
        device_id="device-1",
        expires_at=at,
    )
    assert await repo.create_capture_session(ctx.store, session)
    await repo.commit_capture_session(
        ctx.store,
        session.id,
        [CaptureSessionMember(source_id="camera:1", order=0, shot_id="shot_1")],
        at,
    )

    await capture_session_service.record_judge_outcome(
        ctx,
        session.id,
        "shot_1",
        Verdict(shot_id="shot_1", criteria_met=False, feedback="Not yet."),
    )

    stored = await repo.get_experiment(ctx.store, experiment.id)
    assert stored.status is ExperimentStatus.OPEN
    assert stored.result_shot_ids == ["shot_1"]
    evaluated = await repo.get_capture_session(ctx.store, session.id)
    assert evaluated.evaluated_at is not None
    assert evaluated.representative_result_shot_id == "shot_1"


async def test_terminal_media_counts_as_a_batch_outcome_and_settles(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "u-terminal-member"
    await repo.put_user(ctx.store, User(id=user_id, email="terminal@example.test"))
    experiment = Experiment(
        id="experiment_terminal_member",
        user_id=user_id,
        technique_id="low_key",
        type=ExperimentType.REPRODUCE,
        title="Repeat low key",
        brief="Keep most of the frame dark.",
        why_now="A Keeper supports it.",
        criteria=Criteria(vision=["low_key"]),
    )
    assert await repo.create_open_experiment(ctx.store, experiment)
    session = CaptureSession(
        id="capture_terminal_member",
        user_id=user_id,
        experiment_id=experiment.id,
        device_id="device-1",
        expires_at=now(),
    )
    assert await repo.create_capture_session(ctx.store, session)
    await repo.commit_capture_session(
        ctx.store,
        session.id,
        [CaptureSessionMember(source_id="camera:broken", order=0)],
        now(),
    )
    shot = Shot(
        id="shot_broken",
        user_id=user_id,
        kind=ShotKind.PHOTO,
        source=ShotSource.ANDROID,
        source_id="camera:broken",
        filename="broken.jpg",
        mime_type="image/jpeg",
        experiment_id=experiment.id,
        capture_session_id=session.id,
    )
    await repo.put_shot(ctx.store, shot)
    await runs.ensure(ctx, shot)
    await repo.accept_capture_session_member(ctx.store, session.id, shot.source_id, shot.id)

    await runs.terminal(ctx, shot.id, RunStage.INGEST, "Media proved unreadable")

    settled = await repo.get_capture_session(ctx.store, session.id)
    assert settled.status.value == "settled"
    assert settled.members[0].outcome.value == "terminal"
    assert settled.summary["terminal"] == 1
    assert settled.representative_result_shot_id == ""
    stored_experiment = await repo.get_experiment(ctx.store, experiment.id)
    assert stored_experiment.status is ExperimentStatus.OPEN
    assert stored_experiment.result_shot_ids == [shot.id]


async def test_capture_session_settles_and_notifies_once_after_every_run(tmp_path):
    class MobileDelivery:
        def __init__(self):
            self.messages: list[dict[str, str]] = []

        async def send(self, target, payload, *, tag):
            self.messages.append({**payload, "target": target, "tag": tag})
            return True

    delivery = MobileDelivery()
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
        mobile_push=delivery,
    )
    user_id = "u-settle"
    await repo.put_user(ctx.store, User(id=user_id, email="settle@example.test"))
    await repo.put_device(ctx.store, "device-fingerprint", user_id, "Xiaomi")
    await repo.set_device_notification_target(
        ctx.store, "device-fingerprint", "firebase-installation"
    )
    experiment = Experiment(
        id="experiment_settle",
        user_id=user_id,
        technique_id="low_key",
        type=ExperimentType.REPRODUCE,
        title="Repeat low key",
        brief="Keep most of the frame dark.",
        why_now="A marked Keeper supports it.",
        criteria=Criteria(vision=["low_key"], text=["The frame reads as low key"]),
        reference_shot_id="keeper_1",
    )
    assert await repo.create_open_experiment(ctx.store, experiment)
    at = now()
    session = CaptureSession(
        id="capture_settle",
        user_id=user_id,
        experiment_id=experiment.id,
        device_id="device-fingerprint",
        expires_at=at,
    )
    assert await repo.create_capture_session(ctx.store, session)
    members = [
        CaptureSessionMember(source_id=f"camera:{index}", order=index, shot_id=f"shot_{index}")
        for index in range(2)
    ]
    await repo.commit_capture_session(ctx.store, session.id, members, at)
    for member in members:
        shot = Shot(
            id=member.shot_id,
            user_id=user_id,
            kind=ShotKind.PHOTO,
            source=ShotSource.ANDROID,
            source_id=member.source_id,
            filename=f"{member.shot_id}.jpg",
            mime_type="image/jpeg",
            experiment_id=experiment.id,
            capture_session_id=session.id,
        )
        await repo.put_shot(ctx.store, shot)
        await runs.ensure(ctx, shot)
        await capture_session_service.record_judge_outcome(
            ctx,
            session.id,
            shot.id,
            Verdict(
                shot_id=shot.id,
                criteria_met=member.order == 0,
                feedback="Recorded.",
            ),
        )

    for member in members:
        for stage in RunStage:
            await runs.completed(ctx, member.shot_id, stage, f"{stage.value} settled")

    settled = await repo.get_capture_session(ctx.store, session.id)
    assert settled.status.value == "settled"
    assert settled.summary == {
        "members": 2,
        "completed": 2,
        "terminal": 0,
        "criteria_met": 1,
        "criteria_not_met": 1,
        "abstained": 0,
    }
    assert settled.notification_sent_at is not None
    assert len(delivery.messages) == 1
    assert delivery.messages[0]["kind"] == "capture_session"
    technique = next(
        state
        for state in await repo.list_technique_states(ctx.store, user_id)
        if state.technique_id == "low_key"
    )
    assert technique.reproduce_sessions == 1
    assert technique.evaluable_reproduce_sessions == 1
    assert technique.criteria_met_sessions == 1

    await capture_session_service.on_run_settled(ctx, session.id, members[-1].shot_id)
    assert len(delivery.messages) == 1


async def test_reproduce_change_ignores_free_shots_outside_explicit_results(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "u-explicit-change"
    await repo.put_user(ctx.store, User(id=user_id, email="explicit@example.test"))
    baseline_ids = [f"baseline_{index}" for index in range(8)]
    result_ids = [f"result_{index}" for index in range(3)]
    free_ids = [f"free_{index}" for index in range(3)]

    async def store_readable(shot_id: str, *, portrait: bool) -> None:
        await repo.put_shot(
            ctx.store,
            Shot(
                id=shot_id,
                user_id=user_id,
                kind=ShotKind.PHOTO,
                filename=f"{shot_id}.jpg",
                mime_type="image/jpeg",
                grid=GridSpec(
                    cols=7,
                    rows=7,
                    width=800 if portrait else 1200,
                    height=1200 if portrait else 800,
                ),
            ),
        )
        await repo.put_analysis(
            ctx.store,
            Analysis(shot_id=shot_id, user_id=user_id, model="panel-v1"),
        )

    for shot_id in baseline_ids + result_ids:
        await store_readable(shot_id, portrait=False)
    for shot_id in free_ids:
        await store_readable(shot_id, portrait=True)

    experiment = Experiment(
        id="experiment_explicit_change",
        user_id=user_id,
        technique_id="rule_of_thirds",
        type=ExperimentType.REPRODUCE,
        title="Repeat the frame",
        brief="Try the same orientation deliberately.",
        why_now="Your Keeper supports it.",
        criteria=Criteria(text=["Use the same orientation"]),
        baseline=Baseline(
            source="orientation",
            citation="8 of 8 readable shots: landscape",
            at_issue={"landscape": 8},
            calc_version="tendency-2",
            provenance=Provenance(
                shot_ids=baseline_ids,
                sample_size=len(baseline_ids),
                calc_version="tendency-2",
            ),
        ),
        result_shot_ids=result_ids,
        status=ExperimentStatus.COMPLETED,
    )
    await repo.put_experiment(ctx.store, experiment)

    checked = await scout.check_advice(ctx, user_id)

    assert len(checked) == 1
    change = checked[0].change
    assert change is not None
    assert change.state.value == "unchanged"
    assert change.added == 3
