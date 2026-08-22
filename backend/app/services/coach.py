"""What the Coach remembers: constraints the photographer said out loud.

A voice session is the one place the photographer talks *to* the planner.
After each session the Listener pulls out standing facts (no tripod, shoots
at lunch, walks everywhere) and they are merged into ``User.constraints``,
which the Scout's ranking and brief respect from the next quest on. Merge is
pure and tested; extraction is a model call checked by
``scripts/check_listener.py``.
"""

import logging

from app.agents import coach as agent
from app.domain.entities import Constraints, now
from app.infra import repository as repo
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
