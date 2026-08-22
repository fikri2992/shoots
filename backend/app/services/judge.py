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
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "judge"


async def judge(ctx: Context, message: dict) -> None:
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

    try:
        written = await agent.feedback(quest, passed, exif_checks, vision_checks, analysis)
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
        },
        shot_id=shot.id,
        quest_id=quest.id,
    )
    if passed:
        await ctx.bus.publish(
            TOPICS["quest.closed"], {"user_id": shot.user_id, "quest_id": quest.id}
        )
