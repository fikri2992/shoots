"""Scoped Photographer memory through real API, Store, Coach, and recall seams."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    PhotographerSignal,
    PhotographerSignalKind,
    SignalScope,
    SignalSource,
    User,
    now,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.store import InMemoryStore
from app.services import coach, photographer_memory
from app.services.context import Context


def memory_context() -> Context:
    return Context(
        store=InMemoryStore(),
        blobs=None,
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )


async def test_memory_api_is_idempotent_correctable_and_user_isolated():
    ctx = memory_context()
    user = User(id="memory_user", email="memory@example.test")
    other = User(id="other_user", email="other@example.test")
    await repo.put_user(ctx.store, user)
    await repo.put_user(ctx.store, other)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            first = client.post(
                "/api/memory/signals",
                json={"kind": "constraint", "value": "Shoots only on weekends"},
            )
            replay = client.post(
                "/api/memory/signals",
                json={"kind": "constraint", "value": "Shoots only on weekends"},
            )
            corrected = client.post(
                "/api/memory/signals",
                json={
                    "kind": "constraint",
                    "value": "Shoots on weekday evenings",
                    "supersedes_signal_id": first.json()["id"],
                },
            )
            listed = client.get("/api/memory/signals")
            removed = client.delete(f"/api/memory/signals/{corrected.json()['id']}")
            empty = client.get("/api/memory/signals")
    finally:
        main.app.dependency_overrides.clear()

    assert first.status_code == 200, first.text
    assert replay.json()["id"] == first.json()["id"]
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["supersedes_signal_id"] == first.json()["id"]
    assert [item["value"] for item in listed.json()] == ["Shoots on weekday evenings"]
    assert removed.status_code == 204
    assert empty.json() == []
    history = await repo.list_photographer_signals(
        ctx.store,
        user.id,
        include_superseded=True,
    )
    assert len(history) == 2
    assert all(signal.superseded_at is not None for signal in history)
    assert await repo.list_photographer_signals(ctx.store, other.id) == []


async def test_recall_is_scope_bounded_and_reports_missing_intent():
    ctx = memory_context()
    user = User(id="memory_user", email="memory@example.test")
    await repo.put_user(ctx.store, user)
    created = now()
    signals = [
        PhotographerSignal(
            id="global_constraint",
            user_id=user.id,
            kind=PhotographerSignalKind.CONSTRAINT,
            value="tripod",
            source=SignalSource.DIRECT_STATEMENT,
            transcript_digest="transcript-a",
            created_at=created,
        ),
        PhotographerSignal(
            id="shot_intent",
            user_id=user.id,
            scope=SignalScope.SHOT,
            scope_id="shot_a",
            kind=PhotographerSignalKind.INTENT,
            value="Make the empty space feel tense",
            source=SignalSource.PHOTOGRAPHER_ACTION,
            source_event_id="intent_action",
            created_at=created + timedelta(seconds=1),
        ),
        PhotographerSignal(
            id="expired",
            user_id=user.id,
            kind=PhotographerSignalKind.CONSTRAINT,
            value="Temporary rain",
            source=SignalSource.PHOTOGRAPHER_ACTION,
            source_event_id="weather_action",
            expires_at=created - timedelta(seconds=1),
        ),
    ]
    for signal in signals:
        await photographer_memory.apply_photographer_signal(ctx, signal)

    shot_recall = await photographer_memory.recall(
        ctx,
        user.id,
        "coach",
        "discuss_shot",
        SignalScope.SHOT,
        "shot_a",
    )
    other_recall = await photographer_memory.recall(
        ctx,
        user.id,
        "coach",
        "discuss_shot",
        SignalScope.SHOT,
        "shot_b",
    )
    source_recall = await photographer_memory.recall(
        ctx,
        user.id,
        "source_authority",
        "classify",
        SignalScope.SHOT,
        "shot_a",
    )
    constraints = await photographer_memory.constraints_for(
        ctx,
        user.id,
        role="coach",
        purpose="discuss_shot",
        scope=SignalScope.SHOT,
        scope_id="shot_a",
    )

    assert [signal.id for signal in shot_recall.signals] == ["shot_intent", "global_constraint"]
    assert shot_recall.blind_spots == []
    assert [signal.id for signal in other_recall.signals] == ["global_constraint"]
    assert other_recall.blind_spots == ["No explicit Intent is stored for this scope."]
    assert source_recall.signals == []
    assert shot_recall.input_signal_ids == ["shot_intent", "global_constraint"]
    assert constraints.missing_gear == ["tripod"]
    assert constraints.notes == ["Explicit Intent: Make the empty space feel tense"]


async def test_live_remember_requires_literal_support_and_announces_exact_storage():
    ctx = memory_context()
    user = User(id="memory_user", email="memory@example.test")
    await repo.put_user(ctx.store, user)
    transcript = [
        {"role": "user", "text": "I do not have a tripod, and I shoot after work."},
        {"role": "model", "text": "I can remember that."},
    ]

    result = await coach.run_tool(
        ctx,
        user.id,
        "remember",
        {
            "missing_gear": ["tripod", "flash"],
            "notes": ["Shoots after work"],
            "statement": "I do not have a tripod, and I shoot after work.",
        },
        transcript=transcript,
    )
    unsupported = await coach.run_tool(
        ctx,
        user.id,
        "remember",
        {
            "missing_gear": ["telephoto"],
            "statement": "I never said this.",
        },
        transcript=transcript,
    )
    remembered = await photographer_memory.constraints_for(
        ctx,
        user.id,
        role="coach",
        purpose="remembered_constraints",
    )

    assert result["ok"] is True
    assert result["remembered"] == ["tripod", "Shoots after work"]
    assert "flash" not in result["remembered"]
    assert coach.summarise_tool("remember", result) == ("remembered: tripod · Shoots after work")
    assert unsupported["ok"] is False
    assert remembered.missing_gear == ["tripod"]
    assert remembered.notes == ["Shoots after work"]
    stored = await repo.list_photographer_signals(ctx.store, user.id)
    assert all(signal.transcript_digest for signal in stored)
    assert all(signal.source is SignalSource.DIRECT_STATEMENT for signal in stored)


async def test_current_signal_reads_filter_expiry_rank_exact_scope_and_reject_unknown_roles():
    ctx = memory_context()
    user = User(id="memory_user", email="memory@example.test")
    await repo.put_user(ctx.store, user)
    created = now()
    expired = PhotographerSignal(
        id="expired_intent",
        user_id=user.id,
        scope=SignalScope.SHOOT,
        scope_id="shoot_a",
        kind=PhotographerSignalKind.INTENT,
        value="Old intent",
        source=SignalSource.PHOTOGRAPHER_ACTION,
        source_event_id="expired_intent_action",
        created_at=created - timedelta(days=2),
        expires_at=created - timedelta(days=1),
    )
    exact = PhotographerSignal(
        id="exact_intent",
        user_id=user.id,
        scope=SignalScope.SHOOT,
        scope_id="shoot_a",
        kind=PhotographerSignalKind.INTENT,
        value="Keep the frame quiet",
        source=SignalSource.PHOTOGRAPHER_ACTION,
        source_event_id="exact_intent_action",
        created_at=created - timedelta(days=1),
    )
    globals_ = [
        PhotographerSignal(
            id=f"global_constraint_{index}",
            user_id=user.id,
            kind=PhotographerSignalKind.CONSTRAINT,
            value=f"Constraint {index}",
            source=SignalSource.PHOTOGRAPHER_ACTION,
            source_event_id=f"global_constraint_action_{index}",
            created_at=created + timedelta(seconds=index),
        )
        for index in range(photographer_memory.MAX_RECALL_SIGNALS)
    ]
    for signal in [expired, exact, *globals_]:
        await photographer_memory.apply_photographer_signal(ctx, signal)

    current = await repo.list_photographer_signals(ctx.store, user.id)
    history = await repo.list_photographer_signals(
        ctx.store,
        user.id,
        include_expired=True,
    )
    recalled = await photographer_memory.recall(
        ctx,
        user.id,
        "shoot_scout",
        "shoot_intervention",
        SignalScope.SHOOT,
        "shoot_a",
    )

    assert expired.id not in {signal.id for signal in current}
    assert expired.id in {signal.id for signal in history}
    assert recalled.input_signal_ids[0] == exact.id
    assert len(recalled.signals) == photographer_memory.MAX_RECALL_SIGNALS
    assert expired.id not in recalled.input_signal_ids
    with pytest.raises(
        photographer_memory.SignalConflict, match="Unknown Photographer memory role"
    ):
        await photographer_memory.recall(ctx, user.id, "shoot_scout_typo", "shoot_intervention")
