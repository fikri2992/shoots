"""Scoped, attributable Photographer memory and bounded role-specific recall."""

import hashlib

from app.domain.entities import (
    Constraints,
    MemoryRecall,
    PhotographerSignal,
    PhotographerSignalKind,
    SignalScope,
    SignalSource,
    now,
)
from app.infra import repository as repo
from app.services.context import Context

MEMORY_VERSION = "photographer-memory-1"
MAX_RECALL_SIGNALS = 12
GEAR = ("tripod", "telephoto", "macro", "flash")


class SignalConflict(ValueError):
    pass


def stable_signal_id(
    user_id: str,
    scope: SignalScope,
    scope_id: str,
    kind: PhotographerSignalKind,
    value: str,
    provenance: str,
) -> str:
    payload = "\0".join((user_id, scope.value, scope_id, kind.value, value, provenance))
    return f"signal_{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


async def apply_photographer_signal(
    ctx: Context,
    signal: PhotographerSignal,
) -> PhotographerSignal:
    """Store one signal idempotently and supersede only an explicit predecessor."""
    signal.value = " ".join(signal.value.split()).strip()[:500]
    if not signal.value:
        raise SignalConflict("Photographer Signal value is empty")
    if signal.scope is SignalScope.PHOTOGRAPHER and signal.scope_id:
        raise SignalConflict("Photographer-scoped memory cannot carry another scope id")
    if signal.scope is not SignalScope.PHOTOGRAPHER and not signal.scope_id:
        raise SignalConflict(f"{signal.scope.value} memory requires a scope id")
    if signal.source is SignalSource.DIRECT_STATEMENT and not (
        signal.transcript_digest or signal.source_event_id
    ):
        raise SignalConflict("A direct statement requires transcript or event provenance")
    if signal.source is SignalSource.CONFIRMED_SUGGESTION and signal.confirmed_at is None:
        raise SignalConflict("A confirmed suggestion requires confirmation time")
    if signal.source is SignalSource.PHOTOGRAPHER_ACTION and not signal.source_event_id:
        raise SignalConflict("A Photographer action requires event provenance")
    if await repo.find_user(ctx.store, signal.user_id) is None:
        raise repo.UnknownEntity(f"Photographer {signal.user_id}")

    previous = None
    if signal.supersedes_signal_id:
        previous = await repo.find_photographer_signal(ctx.store, signal.supersedes_signal_id)
        if previous is None or previous.user_id != signal.user_id:
            raise SignalConflict("The superseded Photographer Signal was not found")
        if previous.kind is not signal.kind:
            raise SignalConflict("A Photographer Signal can supersede only the same kind")

    stored = await repo.put_photographer_signal_once(ctx.store, signal)
    if previous is not None and previous.superseded_at is None:
        previous.superseded_at = stored.created_at
        await repo.put_photographer_signal(ctx.store, previous)
    await repo.record_photographer_signal(ctx.store, stored, "signal_stored")
    return stored


async def retract(
    ctx: Context,
    user_id: str,
    signal_id: str,
) -> PhotographerSignal:
    signal = await repo.find_photographer_signal(ctx.store, signal_id)
    if signal is None or signal.user_id != user_id:
        raise repo.UnknownEntity(f"Photographer Signal {signal_id}")
    if signal.superseded_at is None:
        signal.superseded_at = now()
        await repo.put_photographer_signal(ctx.store, signal)
        await repo.record_photographer_signal(ctx.store, signal, "signal_retracted")
    return signal


async def recall(
    ctx: Context,
    user_id: str,
    role: str,
    purpose: str,
    scope: SignalScope = SignalScope.PHOTOGRAPHER,
    scope_id: str = "",
) -> MemoryRecall:
    current = now()
    allowed_kinds = _allowed_kinds(role)
    candidates = []
    for signal in await repo.list_photographer_signals(ctx.store, user_id):
        if signal.expires_at is not None and signal.expires_at <= current:
            continue
        if signal.kind not in allowed_kinds:
            continue
        global_signal = signal.scope is SignalScope.PHOTOGRAPHER
        exact_signal = signal.scope is scope and signal.scope_id == scope_id
        if global_signal or exact_signal:
            candidates.append(signal)
    candidates = candidates[:MAX_RECALL_SIGNALS]
    blind_spots = []
    if not any(signal.kind is PhotographerSignalKind.INTENT for signal in candidates):
        blind_spots.append("No explicit Intent is stored for this scope.")
    return MemoryRecall(
        role=role,
        purpose=purpose,
        scope=scope,
        scope_id=scope_id,
        signals=candidates,
        input_signal_ids=[signal.id for signal in candidates],
        blind_spots=blind_spots,
        memory_version=MEMORY_VERSION,
    )


async def constraints_for(
    ctx: Context,
    user_id: str,
    *,
    scope: SignalScope = SignalScope.PHOTOGRAPHER,
    scope_id: str = "",
) -> Constraints:
    user = await repo.get_user(ctx.store, user_id)
    remembered = await recall(ctx, user_id, "scout", "experiment_selection", scope, scope_id)
    missing_gear = list(user.constraints.missing_gear)
    notes = list(user.constraints.notes)
    for signal in reversed(remembered.signals):
        value = signal.value.strip()
        if signal.kind is PhotographerSignalKind.CONSTRAINT:
            if value in GEAR and value not in missing_gear:
                missing_gear.append(value)
            elif value and value not in notes:
                notes.append(value)
        elif signal.kind is PhotographerSignalKind.INTENT:
            note = f"Explicit Intent: {value}"
            if note not in notes:
                notes.append(note)
        elif signal.kind is PhotographerSignalKind.PREFERENCE:
            note = f"Explicit preference: {value}"
            if note not in notes:
                notes.append(note)
    return Constraints(
        missing_gear=missing_gear,
        notes=notes[-8:],
        updated_at=max(
            (
                signal.created_at
                for signal in remembered.signals
                if signal.kind
                in {
                    PhotographerSignalKind.CONSTRAINT,
                    PhotographerSignalKind.INTENT,
                    PhotographerSignalKind.PREFERENCE,
                }
            ),
            default=user.constraints.updated_at,
        ),
    )


def transcript_digest(transcript: list[dict]) -> str:
    text = "\n".join(
        f"{line.get('role', '')}:{' '.join(str(line.get('text', '')).split())}"
        for line in transcript
    )
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def quote_is_direct(quote: str, transcript: list[dict]) -> bool:
    needle = " ".join(quote.casefold().split()).strip(" .")
    return bool(needle) and any(
        needle in " ".join(str(line.get("text", "")).casefold().split()).strip(" .")
        for line in transcript
        if line.get("role") == "user"
    )


def _allowed_kinds(role: str) -> set[PhotographerSignalKind]:
    if role == "source_authority":
        return {PhotographerSignalKind.SOURCE_ROLE}
    if role in {"scout", "shoot_scout"}:
        return {
            PhotographerSignalKind.INTENT,
            PhotographerSignalKind.CONSTRAINT,
            PhotographerSignalKind.PREFERENCE,
        }
    if role == "coach":
        return {
            PhotographerSignalKind.INTENT,
            PhotographerSignalKind.CONSTRAINT,
            PhotographerSignalKind.PREFERENCE,
        }
    return set(PhotographerSignalKind)
