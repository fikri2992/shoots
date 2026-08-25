"""What the Coach remembers: constraints the photographer said out loud.

A voice session is the one place the photographer talks *to* the planner.
After each session the Listener pulls out standing facts (no tripod, shoots
at lunch, walks everywhere) and they are merged into ``User.constraints``,
which the Scout's ranking and brief respect from the next experiment on. Merge is
pure and tested; extraction is a model call checked by
``scripts/check_listener.py``.
"""

import logging

from app.agents import coach as agent
from app.domain import taxonomy
from app.domain.entities import Constraints, now
from app.infra import repository as repo
from app.services import scout
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


async def remember(ctx: Context, user_id: str, transcript: list[dict]) -> Constraints | None:
    """Listen to a finished session; returns the merged constraints if anything changed."""
    if not any(line["role"] == "user" and line["text"].strip() for line in transcript):
        return None
    user = await repo.get_user(ctx.store, user_id)
    try:
        heard = await agent.listen(transcript, user_id)
    except Exception:  # a missed note must never fail the session
        logger.exception("listener failed for %s", user_id)
        return None
    merged = merge(user.constraints, heard.missing_gear, heard.notes)
    if (
        merged.missing_gear == user.constraints.missing_gear
        and merged.notes == user.constraints.notes
    ):
        return None
    user.constraints = merged
    await repo.put_user(ctx.store, user)
    await repo.record(
        ctx.store,
        user_id,
        AGENT,
        "noted",
        {"missing_gear": merged.missing_gear, "notes": merged.notes},
    )
    return merged


# --- the Coach's tools (Gemini Live function calls) -------------------------------


async def run_tool(ctx: Context, user_id: str, name: str, args: dict) -> dict:
    """Dispatch one Live function call. Returns what the model reads back."""
    if name == "issue_quest":
        technique_id = str(args.get("technique_id", "") or "").strip().lower()
        reason = str(args.get("reason", "") or "").strip()[:200]
        if technique_id and technique_id not in taxonomy.BY_ID:
            return {"ok": False, "error": f"unknown technique id {technique_id}"}
        experiment = await scout.issue(ctx, user_id, force=True, technique_id=technique_id)
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
        user = await repo.get_user(ctx.store, user_id)
        merged = merge(
            user.constraints,
            [str(g) for g in args.get("missing_gear", []) or []],
            [str(n) for n in args.get("notes", []) or []],
        )
        user.constraints = merged
        await repo.put_user(ctx.store, user)
        await repo.record(
            ctx.store,
            user_id,
            AGENT,
            "noted",
            {"missing_gear": merged.missing_gear, "notes": merged.notes},
        )
        return {"ok": True, "missing_gear": merged.missing_gear, "notes": merged.notes}
    if name == "skill_map":
        skills = await repo.list_skills(ctx.store, user_id)
        by_status: dict[str, list[str]] = {}
        for state in skills:
            by_status.setdefault(state.status.value, []).append(
                f"{taxonomy.BY_ID[state.technique_id].name} (best {state.best_score}/10)"
                if state.technique_id in taxonomy.BY_ID
                else state.technique_id
            )
        attempted = {s.technique_id for s in skills if s.status.value != "unexplored"}
        unlocked = [t.name for t in taxonomy.unlocked(attempted) if not t.video_only][:12]
        return {"ok": True, "by_status": by_status, "unlocked_next": unlocked}
    return {"ok": False, "error": f"unknown tool {name}"}


def summarise_tool(name: str, result: dict) -> str:
    """One line for the phone and the feed."""
    if not result.get("ok"):
        return f"{name}: {result.get('error', 'failed')}"
    if name == "issue_quest":
        return f"issued a experiment: {result['title']}"
    if name == "remember":
        bits = []
        if result.get("missing_gear"):
            bits.append("no " + ", ".join(result["missing_gear"]))
        bits += result.get("notes", [])[-2:]
        return "remembered: " + " · ".join(bits)
    if name == "skill_map":
        count = sum(len(v) for v in result.get("by_status", {}).values())
        return f"read the skill map ({count} techniques attempted)"
    return name
