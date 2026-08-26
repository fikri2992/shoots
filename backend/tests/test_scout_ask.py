"""Scout Ask through real decision, API, Store, memory, and Explore seams."""

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
from app.services import scout_answers, shoot_scout
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


async def test_ask_records_photographer_intent_and_opens_supported_explore(tmp_path):
    ctx, user, shoot, receipt = await seed(tmp_path)
    decision = await shoot_scout.decide(ctx, shoot, receipt)
    assert decision.route.value == "ask"
    assert decision.question.prompt == "Which decision were you exploring in this Shoot?"
    assert [option.technique_id for option in decision.question.options] == [
        "backlight",
        "negative_space",
        "",
    ]
    assert decision.question.options[-1].id == "just_shooting"
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
            answered = client.post(
                f"/api/shoots/{shoot.id}/scout-answer",
                json={"revision": 1, "option_id": "technique_backlight"},
            )
            assert answered.status_code == 200, answered.text
            body = answered.json()
            assert body["technique_id"] == "backlight"
            assert body["experiment_id"]
            replay = client.post(
                f"/api/shoots/{shoot.id}/scout-answer",
                json={"revision": 1, "option_id": "technique_backlight"},
            )
            assert replay.status_code == 200
            assert replay.json()["id"] == body["id"]
            conflict = client.post(
                f"/api/shoots/{shoot.id}/scout-answer",
                json={"revision": 1, "option_id": "just_shooting"},
            )
            assert conflict.status_code == 409
    finally:
        main.app.dependency_overrides.clear()

    signals = await repo.list_photographer_signals(ctx.store, user.id)
    assert len(signals) == 1
    assert signals[0].scope.value == "shoot"
    assert signals[0].scope_id == shoot.id
    assert signals[0].kind.value == "intent"
    assert signals[0].value == "I was exploring Backlight."
    experiment = await repo.get_experiment(ctx.store, body["experiment_id"])
    assert experiment.type.value == "explore"
    assert experiment.technique_id == "backlight"
    assert experiment.criteria.text == []
    assert experiment.warrant_shot_ids == ["ask_shot_1", "ask_shot_2", "ask_shot_3"]


async def test_just_shooting_records_intent_without_inventing_an_experiment(tmp_path):
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

    answer = await scout_answers.answer(ctx, user.id, shoot.id, 1, "just_shooting")

    assert answer.experiment_id == ""
    assert answer.detail == "Intent recorded; no Experiment was requested."
    assert await repo.open_experiment(ctx.store, user.id) is None
    signals = await repo.list_photographer_signals(ctx.store, user.id)
    assert [signal.value for signal in signals] == ["I was just shooting freely."]
