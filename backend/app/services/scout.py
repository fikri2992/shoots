"""Scout stage: issue the next quest.

Triggered by the daily tick, by ``quest.closed``, and by the dashboard's
"issue now" for demos. One open quest per user (decision 6): if one is open
this is a no-op, so every trigger is safe to repeat.
"""

import logging
from datetime import timedelta

from app.agents import scout as agent
from app.config import settings
from app.domain import scout as rules
from app.domain import skills as skill_rules
from app.domain import timing
from app.domain.entities import Quest, QuestStatus, QuestTiming, new_id, now
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.services import notify
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "scout"
#: How many recent quests' techniques are skipped when choosing the next one.
RECENT_QUESTS = 6


async def issue(ctx: Context, user_id: str, force: bool = False) -> Quest | None:
    """Issue one quest for the user if none is open. Returns it, or None."""
    open_quest = await repo.open_quest(ctx.store, user_id)
    if open_quest and not force:
        logger.info("scout: %s already has open quest %s", user_id, open_quest.id)
        return None

    skills = {s.technique_id: s for s in await repo.list_skills(ctx.store, user_id)}
    decayed = skill_rules.decay(skills, now(), settings.skill_decay_days)
    for state in decayed:
        await repo.put_skill(ctx.store, state)

    recent = [
        q.technique_id for q in await repo.list_quests(ctx.store, user_id, limit=RECENT_QUESTS)
    ]
    technique = rules.choose(skills, recent)
    if technique is None:
        await repo.record(ctx.store, user_id, AGENT, "nothing_to_issue", {"recent": recent})
        return None

    why = rules.why_now(technique, skills)
    critiques = await _recent_critiques(ctx, user_id)

    research = await agent.research(technique)
    out = await agent.write(technique, why, critiques, research, skills)

    quest = Quest(
        id=new_id("quest"),
        user_id=user_id,
        technique_id=technique.id,
        title=out.title.strip()[:60] or technique.name,
        brief=out.brief.strip()[:2000],
        why_now=(out.why_now.strip() or why)[:500],
        criteria=agent.criteria_for(technique, out.criteria_text),
        references=agent.pick_references(out, research),
        status=QuestStatus.OPEN,
        due_at=now() + timedelta(days=settings.quest_ttl_days),
    )
    user = await repo.get_user(ctx.store, user_id)
    when = timing.deliver_at(technique.light, now(), user.last_latitude, user.last_longitude)
    quest.deliver_at = when.at
    quest.timing = QuestTiming(
        light=when.light, reason=when.reason, anchor=when.anchor, anchor_at=when.anchor_at
    )
    await repo.put_quest(ctx.store, quest)
    await repo.record(
        ctx.store,
        user_id,
        AGENT,
        "issued",
        {
            "technique_id": technique.id,
            "title": quest.title,
            "why": why,
            "references": len(quest.references),
            "hard_criteria": agent.hard_criteria_text(technique),
            "deliver_at": quest.deliver_at.isoformat() if quest.deliver_at else "",
            "timing": when.reason,
        },
        quest_id=quest.id,
    )
    await deliver_if_due(ctx, quest)
    await ctx.bus.publish(TOPICS["quest.issued"], {"user_id": user_id, "quest_id": quest.id})
    return quest


async def deliver_if_due(ctx: Context, quest: Quest) -> bool:
    """Push the quest if its moment has come. The quest exists in the store
    either way; this is only about when the phone buzzes."""
    if quest.delivered_at or quest.status is not QuestStatus.OPEN:
        return False
    if quest.deliver_at and quest.deliver_at > now() + timing.SOON:
        return False
    await notify.quest_issued(ctx, quest)
    quest.delivered_at = now()
    await repo.put_quest(ctx.store, quest)
    await repo.record(
        ctx.store,
        quest.user_id,
        AGENT,
        "delivered",
        {"technique_id": quest.technique_id, "timing": quest.timing.reason if quest.timing else ""},
        quest_id=quest.id,
    )
    return True


async def deliver_due(ctx: Context) -> int:
    """The frequent tick: every open, undelivered quest whose time has come."""
    delivered = 0
    for user in await repo.list_users(ctx.store):
        quest = await repo.open_quest(ctx.store, user.id)
        if quest and await deliver_if_due(ctx, quest):
            delivered += 1
    return delivered


async def skip(ctx: Context, user_id: str, quest_id: str) -> Quest:
    """The human gate. Logged, never deleted; the next tick issues another."""
    quest = await repo.get_quest(ctx.store, quest_id)
    if quest.user_id != user_id:
        raise repo.UnknownEntity(f"quest {quest_id}")
    if quest.status is QuestStatus.OPEN:
        quest.status = QuestStatus.SKIPPED
        quest.closed_at = now()
        await repo.put_quest(ctx.store, quest)
        await repo.record(
            ctx.store,
            user_id,
            "user",
            "skipped",
            {"technique_id": quest.technique_id},
            quest_id=quest.id,
        )
    return quest


async def expire(ctx: Context, user_id: str) -> list[Quest]:
    """Open quests past due become expired. Called by the daily tick."""
    expired: list[Quest] = []
    current = now()
    for quest in await repo.list_quests(ctx.store, user_id):
        if quest.status is QuestStatus.OPEN and quest.due_at and quest.due_at < current:
            quest.status = QuestStatus.EXPIRED
            quest.closed_at = current
            await repo.put_quest(ctx.store, quest)
            await repo.record(
                ctx.store,
                user_id,
                "scheduler",
                "expired",
                {"technique_id": quest.technique_id},
                quest_id=quest.id,
            )
            expired.append(quest)
    return expired


async def on_quest_closed(ctx: Context, message: dict) -> None:
    await issue(ctx, message["user_id"])


async def _recent_critiques(ctx: Context, user_id: str, limit: int = 5) -> list[str]:
    shots = await repo.list_shots(ctx.store, user_id, limit=limit * 2)
    critiques: list[str] = []
    for shot in shots:
        analysis = await repo.find_analysis(ctx.store, shot.id)
        if analysis and analysis.critique:
            critiques.append(f"{shot.filename}: {analysis.critique}")
        if len(critiques) >= limit:
            break
    return critiques
