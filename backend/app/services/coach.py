"""Attributable constraints the Photographer said out loud."""

import logging

from app.agents import coach as agent
from app.domain import taxonomy
from app.domain.entities import (
    Constraints,
    PhotographerSignal,
    PhotographerSignalKind,
    SignalScope,
    SignalSource,
    now,
)
from app.infra import repository as repo
from app.services import photographer_memory, scout
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "coach"
MAX_NOTES = 8
GEAR = ("tripod", "telephoto", "macro", "flash")


def merge(existing: Constraints, missing_gear: list[str], notes: list[str]) -> Constraints:
    """Union of gear, newest notes last, deduped case-insensitively, capped."""
    gear = [g for g in existing.missing_gear if g in GEAR]
    for item in missing_gear:
        item = item.strip().lower()
        if item in GEAR and item not in gear:
            gear.append(item)
    kept = list(existing.notes)
    seen = {n.strip().lower() for n in kept}
    for note in notes:
        text = " ".join(note.split()).strip().rstrip(".")
        if text and text.lower() not in seen:
            kept.append(text)
            seen.add(text.lower())
    return Constraints(missing_gear=gear, notes=kept[-MAX_NOTES:], updated_at=now())


async def remember(
    ctx: Context,
    user_id: str,
    transcript: list[dict],
) -> list[PhotographerSignal]:
    """Store only Listener candidates backed by literal Photographer words."""
    if not any(line["role"] == "user" and line["text"].strip() for line in transcript):
        return []
    try:
        heard = await agent.listen(transcript, user_id)
    except Exception:  # a missed note must never fail the session
        logger.exception("listener failed for %s", user_id)
        return []
    candidates = [
        (fact.value, fact.quote)
        for fact in heard.facts
        if fact.kind is PhotographerSignalKind.CONSTRAINT
    ]
    return await _store_direct_constraints(
        ctx,
        user_id,
        transcript,
        candidates,
    )


# --- the Coach's tools (Gemini Live function calls) -------------------------------


async def run_tool(
    ctx: Context,
    user_id: str,
    name: str,
    args: dict,
    *,
    transcript: list[dict] | None = None,
) -> dict:
    """Dispatch one Live function call. Returns what the model reads back."""
    if name == "issue_experiment":
        technique_id = str(args.get("technique_id", "") or "").strip().lower()
        reason = str(args.get("reason", "") or "").strip()[:200]
        if technique_id and technique_id not in taxonomy.BY_ID:
            return {"ok": False, "error": f"unknown technique id {technique_id}"}
        experiment = await scout.issue(
            ctx,
            user_id,
            force=True,
            technique_id=technique_id,
            requested_reason=reason,
        )
        if experiment is None:
            return {"ok": False, "error": "nothing could be issued"}
        await repo.record(
            ctx.store,
            user_id,
            AGENT,
            "issued_by_voice",
            {"technique_id": experiment.technique_id, "title": experiment.title, "reason": reason},
            experiment_id=experiment.id,
        )
        return {
            "ok": True,
            "experiment_id": experiment.id,
            "title": experiment.title,
            "technique_id": experiment.technique_id,
            "first_step": experiment.brief.split("\n", 1)[0],
            "lands_at": experiment.deliver_at.isoformat() if experiment.deliver_at else "now",
        }
    if name == "remember":
        statement = str(args.get("statement", "") or "").strip()
        if transcript is None or not photographer_memory.quote_is_direct(statement, transcript):
            return {
                "ok": False,
                "error": "The memory was not stored because its Photographer quote was missing.",
            }
        values = [
            str(value).strip().lower()
            for value in args.get("missing_gear", []) or []
            if str(value).strip().lower() in GEAR
            and _gear_is_direct(str(value).strip().lower(), statement)
        ]
        values += [
            " ".join(str(value).split()).strip().rstrip(".")
            for value in args.get("notes", []) or []
            if str(value).strip()
        ]
        stored = await _store_direct_constraints(
            ctx,
            user_id,
            transcript,
            [(value, statement) for value in values],
        )
        if not stored:
            return {"ok": False, "error": "No new direct Photographer fact was stored."}
        return {
            "ok": True,
            "remembered": [signal.value for signal in stored],
            "signal_ids": [signal.id for signal in stored],
        }
    if name == "technique_map":
        states = await repo.list_technique_states(ctx.store, user_id)
        by_status: dict[str, list[str]] = {}
        for state in states:
            # How often the Evidence corroborated it, never a score. The Coach
            # speaks out loud, so a number handed to it here is a number the
            # photographer hears - and one frame demonstrating six Techniques
            # gave the same score to all six (decision 46).
            name_or_id = (
                taxonomy.BY_ID[state.technique_id].name
                if state.technique_id in taxonomy.BY_ID
                else state.technique_id
            )
            seen = f" (seen {state.attempts}, confirmed {state.corroborated})"
            by_status.setdefault(state.status.value, []).append(name_or_id + seen)
        return {"ok": True, "by_status": by_status}
    return {"ok": False, "error": f"unknown tool {name}"}


def summarise_tool(name: str, result: dict) -> str:
    """One line for the phone and the feed."""
    if not result.get("ok"):
        return f"{name}: {result.get('error', 'failed')}"
    if name == "issue_experiment":
        return f"issued an experiment: {result['title']}"
    if name == "remember":
        return "remembered: " + " · ".join(result.get("remembered", [])[-3:])
    if name == "technique_map":
        count = sum(len(v) for v in result.get("by_status", {}).values())
        return f"read the technique map ({count} techniques observed)"
    return name


async def _store_direct_constraints(
    ctx: Context,
    user_id: str,
    transcript: list[dict],
    candidates: list[tuple[str, str]],
) -> list[PhotographerSignal]:
    digest = photographer_memory.transcript_digest(transcript)
    current = await repo.list_photographer_signals(ctx.store, user_id)
    existing_values = {
        signal.value.casefold()
        for signal in current
        if signal.kind is PhotographerSignalKind.CONSTRAINT
        and signal.scope is SignalScope.PHOTOGRAPHER
    }
    stored: list[PhotographerSignal] = []
    for raw_value, quote in candidates:
        if not photographer_memory.quote_is_direct(quote, transcript):
            continue
        value = " ".join(raw_value.split()).strip().rstrip(".")
        gear = value.casefold()
        if gear in GEAR:
            value = gear
        if not value or value.casefold() in existing_values:
            continue
        signal_id = photographer_memory.stable_signal_id(
            user_id,
            SignalScope.PHOTOGRAPHER,
            "",
            PhotographerSignalKind.CONSTRAINT,
            value,
            f"{digest}:{quote}",
        )
        signal = await photographer_memory.apply_photographer_signal(
            ctx,
            PhotographerSignal(
                id=signal_id,
                user_id=user_id,
                kind=PhotographerSignalKind.CONSTRAINT,
                value=value,
                source=SignalSource.DIRECT_STATEMENT,
                transcript_digest=digest,
            ),
        )
        stored.append(signal)
        existing_values.add(value.casefold())
    return stored


def _gear_is_direct(gear: str, statement: str) -> bool:
    words = statement.casefold()
    denied = any(
        phrase in words
        for phrase in ("no ", "don't have", "do not have", "without", "lack")
    )
    return gear in words and denied
