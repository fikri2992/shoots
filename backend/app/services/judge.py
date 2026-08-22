"""Judge stage: ``media.analyzed`` → verdict on the open quest → ``quest.closed``.

Runs alongside the Cartographer on the same topic. Skips quietly when the
user has no open quest or the shot is not a submission. A shot is judged
once: a second delivery finds its verdict already on the quest.
"""

import logging

from app.agents import judge as agent
from app.config import settings
from app.domain import judge as rules
from app.domain.entities import QuestStatus, Verdict, now
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.infra.storage import GRIDDED
from app.services import notify
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "judge"


async def judge(ctx: Context, message: dict) -> None:
    """Judge if there is something to judge, then always publish ``media.judged``
    so the Scribe writes the review back with whatever verdict exists."""
    await _judge(ctx, message)
    await ctx.bus.publish(TOPICS["media.judged"], {"shot_id": message["shot_id"]})


async def _judge(ctx: Context, message: dict) -> None:
    shot = await repo.get_shot(ctx.store, message["shot_id"])
    quest = await repo.open_quest(ctx.store, shot.user_id)
    if quest is None:
        return
    if not rules.is_submission(shot, quest):
        return
    if any(v.shot_id == shot.id for v in quest.verdicts):
        logger.info("judge: %s already judged for %s", shot.id, quest.id)
        return

    analysis = await repo.find_analysis(ctx.store, shot.id)
    passed, exif_checks, vision_checks = rules.evaluate(
        quest.criteria, shot.exif, analysis, settings.judge_min_confidence
    )

    previous = await _previous_best(ctx, shot, quest.technique_id)
    try:
        images = [await ctx.blobs.read(shot.blobs[GRIDDED])] if GRIDDED in shot.blobs else []
        if previous and GRIDDED in previous[0].blobs and images:
            images.append(await ctx.blobs.read(previous[0].blobs[GRIDDED]))
        written = await agent.feedback(
            quest, passed, exif_checks, vision_checks, analysis, shot, previous, images
        )
        text = written.feedback.strip()
        if written.tip.strip():
            text = f"{text}\n\nNext: {written.tip.strip()}"
    except Exception:  # the verdict must land even if the model does not
        logger.exception("judge: feedback model failed for %s", shot.id)
        lines = rules.describe_checks(exif_checks, vision_checks, settings.judge_min_confidence)
        text = ("Passed. " if passed else "Not yet. ") + "; ".join(lines)

    verdict = Verdict(
        shot_id=shot.id,
        passed=passed,
        exif_checks={k: (None if v is None else bool(v)) for k, v in exif_checks.items()},
        vision_checks=vision_checks,
        feedback=text[:2000],
        compared_with=previous[0].id if previous else "",
    )
    quest.verdicts.append(verdict)
    if passed:
        quest.status = QuestStatus.PASSED
        quest.closed_at = now()
    await repo.put_quest(ctx.store, quest)

    if not shot.quest_id:
        shot.quest_id = quest.id
        await repo.put_shot(ctx.store, shot)

    await repo.record(
        ctx.store,
        shot.user_id,
        AGENT,
        "passed" if passed else "not_passed",
        {
            "technique_id": quest.technique_id,
            "exif_checks": verdict.exif_checks,
            "vision_checks": {k: round(v, 2) for k, v in vision_checks.items()},
            "compared_with": previous[0].id if previous else "",
        },
        shot_id=shot.id,
        quest_id=quest.id,
    )
    await notify.verdict_given(ctx, quest, verdict)
    if passed:
        await ctx.bus.publish(
            TOPICS["quest.closed"], {"user_id": shot.user_id, "quest_id": quest.id}
        )


async def _previous_best(ctx: Context, shot, technique_id: str):
    """The user's highest-scoring earlier shot that showed this technique, with
    its analysis. The skill graph remembers the shot ids; the rest is a lookup."""
    skills = {s.technique_id: s for s in await repo.list_skills(ctx.store, shot.user_id)}
    state = skills.get(technique_id)
    if state is None:
        return None
    best = None
    for shot_id in state.shot_ids:
        if shot_id == shot.id:
            continue
        candidate = await repo.find_shot(ctx.store, shot_id)
        analysis = await repo.find_analysis(ctx.store, shot_id) if candidate else None
        if candidate is None or analysis is None:
            continue
        if best is None or analysis.score > best[1].score:
            best = (candidate, analysis)
    return best
