"""Scout Recommendation through real decision, API, Store, memory, and Explore seams."""

from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    Analysis,
    Shoot,
    ShootReceipt,
    ShootRecord,
    ShootStatus,
    ShootTechniqueFigure,
    Shot,
    ShotKind,
    ShotStatus,
    TechniqueEvidence,
    User,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import shoot_scout
from app.services.context import Context


async def seed(tmp_path) -> tuple[Context, User, Shoot, ShootReceipt]:
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user = User(id="ask_user", email="ask@example.test")
    await repo.put_user(ctx.store, user)
    shot_ids = []
    for index in range(1, 4):
        shot = Shot(
            id=f"ask_shot_{index}",
            user_id=user.id,
            kind=ShotKind.PHOTO,
            filename=f"ask-{index}.jpg",
            mime_type="image/jpeg",
            status=ShotStatus.ANALYZED,
        )
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
                    ),
                    TechniqueEvidence(
                        technique_id="backlight",
                        confidence=0.85,
                        agreement=2,
                    ),
                ],
            ),
        )
        shot_ids.append(shot.id)
    shoot = Shoot(
        id="shoot_ask",
        user_id=user.id,
        status=ShootStatus.SETTLED,
        revision=1,
        current_record_revision=1,
        ordered_shot_ids=shot_ids,
    )
    await repo.put_shoot(ctx.store, shoot)
    receipt = ShootReceipt(
        calc_version="shoot-receipt-ask",
        summary="Two decisions kept appearing together.",
        shot_count=3,
        scene_count=1,
        readable_shot_count=3,
        repeated=["Negative space and backlighting repeated together."],
        techniques=[
            ShootTechniqueFigure(
                technique_id="negative_space",
                name="Negative space",
                observed_shot_ids=shot_ids,
                corroborated_shot_ids=shot_ids,
            ),
            ShootTechniqueFigure(
                technique_id="backlight",
                name="Backlight",
                observed_shot_ids=shot_ids,
                corroborated_shot_ids=shot_ids,
            ),
        ],
    )
    return ctx, user, shoot, receipt


async def test_recommendation_shows_value_before_acceptance_and_opens_supported_explore(tmp_path):
    ctx, user, shoot, receipt = await seed(tmp_path)
    decision = await shoot_scout.decide(ctx, shoot, receipt)
    assert decision.route.value == "recommend"
    assert decision.recommendation.primary_option_id == "explore_backlight"
    assert [option.technique_id for option in decision.recommendation.options] == [
        "backlight",
        "negative_space",
    ]
    assert await repo.open_experiment(ctx.store, user.id) is None
    await repo.put_shoot_record_once(
        ctx.store,
        ShootRecord(
            shoot_id=shoot.id,
            user_id=user.id,
            revision=shoot.revision,
            shot_ids=list(shoot.ordered_shot_ids),
            receipt=receipt,
            scout=decision,
        ),
    )

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            accepted = client.post(
                f"/api/shoots/{shoot.id}/scout-recommendation",
                json={
                    "revision": 1,
                    "action": "accept",
                    "option_id": "explore_backlight",
                },
            )
            assert accepted.status_code == 200, accepted.text
            body = accepted.json()
            assert body["intervention"]["attempt_state"] == "accepted"
            assert body["intervention"]["technique_id"] == "backlight"
            assert body["experiment"]["technique_id"] == "backlight"
            replay = client.post(
                f"/api/shoots/{shoot.id}/scout-recommendation",
                json={
                    "revision": 1,
                    "action": "accept",
                    "option_id": "explore_backlight",
                },
            )
            assert replay.status_code == 200
            assert replay.json()["experiment"]["id"] == body["experiment"]["id"]
            conflict = client.post(
                f"/api/shoots/{shoot.id}/scout-recommendation",
                json={
                    "revision": 1,
                    "action": "accept",
                    "option_id": "explore_negative_space",
                },
            )
            assert conflict.status_code == 409
    finally:
        main.app.dependency_overrides.clear()

    signals = await repo.list_photographer_signals(ctx.store, user.id)
    assert signals == []
    experiment = await repo.get_experiment(ctx.store, body["experiment"]["id"])
    assert experiment.type.value == "explore"
    assert experiment.technique_id == "backlight"
    assert experiment.criteria.text == []
    assert experiment.warrant_shot_ids == ["ask_shot_1", "ask_shot_2", "ask_shot_3"]


async def test_optional_just_shooting_calibration_records_intent_without_an_experiment(tmp_path):
    ctx, user, shoot, receipt = await seed(tmp_path)
    decision = await shoot_scout.decide(ctx, shoot, receipt)
    await repo.put_shoot_record_once(
        ctx.store,
        ShootRecord(
            shoot_id=shoot.id,
            user_id=user.id,
            revision=shoot.revision,
            shot_ids=list(shoot.ordered_shot_ids),
            receipt=receipt,
            scout=decision,
        ),
    )

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            response = client.post(
                f"/api/shoots/{shoot.id}/scout-recommendation",
                json={"revision": 1, "action": "just_shooting"},
            )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["intervention"]["attempt_state"] == "left"
    assert response.json()["experiment"] is None
    assert await repo.open_experiment(ctx.store, user.id) is None
    signals = await repo.list_photographer_signals(ctx.store, user.id)
    assert [signal.value for signal in signals] == ["I was just shooting freely."]
