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
from app.domain import taxonomy, tendency, timing
from app.domain.entities import Quest, QuestStatus, QuestTiming, TendencyGrade, new_id, now
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.services import notify
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "scout"
#: How many recent quests' techniques are skipped when choosing the next one.
RECENT_QUESTS = 6
#: How far back the Tendency Profile reads. A tendency is about a body of
#: work, so this is deliberately the whole of it rather than a recent window.
TENDENCY_CORPUS = 500


async def issue(
    ctx: Context, user_id: str, force: bool = False, technique_id: str = ""
) -> Quest | None:
    """Issue one quest for the user if none is open. Returns it, or None.
    ``technique_id`` names the technique (the Coach, by voice); otherwise the
    ranking chooses. With ``force`` an open quest is skipped first."""
    open_quest = await repo.open_quest(ctx.store, user_id)
    if open_quest and not force:
        logger.info("scout: %s already has open quest %s", user_id, open_quest.id)
        return None
    if open_quest and force:
        await skip(ctx, user_id, open_quest.id)

    skills = {s.technique_id: s for s in await repo.list_skills(ctx.store, user_id)}
    decayed = skill_rules.decay(skills, now(), settings.skill_decay_days)
    for state in decayed:
        await repo.put_skill(ctx.store, state)

    recent = [
        q.technique_id for q in await repo.list_quests(ctx.store, user_id, limit=RECENT_QUESTS)
    ]
    user = await repo.get_user(ctx.store, user_id)
    profile = await profile_for(ctx, user_id)
    challenge = tendency.challenge_for(profile)
    technique = (
        taxonomy.BY_ID.get(technique_id)
        if technique_id
        else rules.choose(
            skills,
            recent,
            missing_gear=user.constraints.missing_gear,
            prefer=challenge.prefers if challenge else (),
        )
    )
    if technique is None:
        await repo.record(ctx.store, user_id, AGENT, "nothing_to_issue", {"recent": recent})
        return None

    why = rules.why_now(technique, skills)
    # The citation is the point: a challenge that cannot name the arithmetic
    # behind it is the generic advice this product exists to rise above.
    if challenge and challenge.prefers and technique.id in challenge.prefers:
        why = f"{why} Your own work says so: {challenge.citation}."
    critiques = await _recent_critiques(ctx, user_id)

    research = await agent.research(technique)
    out = await agent.write(technique, why, critiques, research, skills, user.constraints)

    quest = Quest(
        id=new_id("quest"),
        user_id=user_id,
        technique_id=technique.id,
        title=out.title.strip()[:60] or technique.name,
        brief=agent.normalise_brief(out.brief)[:2000],
        why_now=(out.why_now.strip() or why)[:500],
        criteria=agent.criteria_for(technique, out.criteria_text),
        references=agent.pick_references(out, research),
        status=QuestStatus.OPEN,
        due_at=now() + timedelta(days=settings.quest_ttl_days),
    )
    # Freeze what this advice was aimed at, so it can be graded later against
    # arithmetic rather than against anybody's impression of how it went.
    if challenge:
        quest.tendency = TendencyGrade(
            source=challenge.source,
            citation=challenge.citation,
            at_issue=_snapshot(profile, challenge.source),
        )
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
            "tendency": challenge.citation if challenge else "",
            "tendency_source": challenge.source if challenge else "",
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


async def profile_for(ctx: Context, user_id: str) -> tendency.Profile:
    """The photographer's Tendency Profile, over everything stored.

    Pure arithmetic on measurements already on disk (``domain/tendency.py``):
    no model is called here.
    """
    shots = await repo.list_shots(ctx.store, user_id, limit=TENDENCY_CORPUS)
    rows = [(shot, await repo.find_analysis(ctx.store, shot.id)) for shot in shots]
    keepers = {shot.id for shot in shots if shot.keeper}
    return tendency.build(rows, keepers)


def _snapshot(profile: tendency.Profile, source: str) -> dict[str, int]:
    """The counts a challenge was aimed at. Dwell has no buckets, so it is
    frozen as the two figures that make up its ratio."""
    if source == "dwell":
        return {"shots": profile.dwell.shots, "scenes": profile.dwell.scenes}
    found = profile.dimensions.get(source)
    return dict(found.counts) if found else {}


async def grade_advice(ctx: Context, user_id: str) -> list[Quest]:
    """Did the Scout's own advice change anything?

    Decision 37. Every quest that named a tendency is compared against where
    that tendency stands now — counts against counts, no model adjudicating —
    and the answer is written on the quest. An agent that never checks its own
    recommendations is a critique queue, not a coach.

    What this does not claim: that moved counts mean better photographs. That
    stays the panel's opinion, and is labelled as one wherever it appears.
    """
    profile = await profile_for(ctx, user_id)
    graded = []
    for quest in await repo.list_quests(ctx.store, user_id, limit=RECENT_QUESTS):
        mark = quest.tendency
        if mark is None or mark.moved is not None or quest.status is QuestStatus.OPEN:
            continue
        if mark.source == "dwell":
            result = _grade_dwell(mark.at_issue, profile.dwell)
        else:
            dimension = tendency.BY_ID.get(mark.source)
            if dimension is None:
                continue
            result = tendency.grade(dimension, mark.at_issue, _snapshot(profile, mark.source))
        mark.moved = result.moved
        mark.outcome = result.outcome
        mark.graded_at = now()
        await repo.put_quest(ctx.store, quest)
        await repo.record(
            ctx.store,
            user_id,
            AGENT,
            "graded",
            {
                "technique_id": quest.technique_id,
                "tendency": mark.source,
                "moved": mark.moved,
                "outcome": mark.outcome,
                "cited": mark.citation,
            },
            quest_id=quest.id,
        )
        graded.append(quest)
    return graded


def _grade_dwell(at_issue: dict[str, int], now_dwell: tendency.Dwell) -> tendency.Grade:
    """Working the scene is a ratio rather than a distribution, so it is graded
    on whether that ratio rose."""
    was_shots, was_scenes = at_issue.get("shots", 0), at_issue.get("scenes", 0)
    added = now_dwell.shots - was_shots
    if added <= 0:
        return tendency.Grade(moved=False, outcome="nothing shot since", added=0)
    scenes = max(1, now_dwell.scenes - was_scenes)
    per_scene = added / scenes
    was = was_shots / was_scenes if was_scenes else 0.0
    if per_scene > was + 0.5:
        return tendency.Grade(
            moved=True,
            outcome=f"{per_scene:.1f} frames a scene since, up from {was:.1f}",
            added=added,
        )
    return tendency.Grade(
        moved=False,
        outcome=f"{per_scene:.1f} frames a scene since, was {was:.1f}",
        added=added,
    )


async def issue_first(ctx: Context, user_id: str) -> Quest | None:
    """The first quest, unprompted.

    A user who has just handed over their first frames has nothing to do next,
    and waiting for tomorrow's tick to say so is the friction this whole thing
    exists to remove. Fires once, on an empty quest history; after that the
    daily tick and ``quest.closed`` are the only sources.
    """
    if await repo.list_quests(ctx.store, user_id, limit=1):
        return None
    quest = await issue(ctx, user_id)
    if quest is not None:
        logger.info("scout: first quest %s for %s", quest.id, user_id)
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
