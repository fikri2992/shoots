"""Judge stage: ``media.analyzed`` → verdict on the open experiment → ``experiment.closed``.

Runs alongside the Cartographer on the same topic. Skips quietly when the
user has no open experiment or the shot is not a submission. A shot is judged
once: a second delivery finds its verdict already on the experiment.
"""

import logging

from app.agents import judge as agent
from app.config import settings
from app.domain import judge as rules
from app.domain.entities import ExperimentStatus, Verdict, now
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
    experiment = await repo.open_experiment(ctx.store, shot.user_id)
    if experiment is None:
        return
    if not rules.is_submission(shot, experiment):
        return
    if any(v.shot_id == shot.id for v in experiment.verdicts):
        logger.info("judge: %s already judged for %s", shot.id, experiment.id)
        return

    analysis = await repo.find_analysis(ctx.store, shot.id)
    passed, exif_checks, vision_checks = rules.evaluate(
        experiment.criteria, shot.exif, analysis, settings.judge_min_confidence
    )

    previous = await _previous_best(ctx, shot, experiment.technique_id)
    try:
        images = [await ctx.blobs.read(shot.blobs[GRIDDED])] if GRIDDED in shot.blobs else []
        if previous and GRIDDED in previous[0].blobs and images:
            images.append(await ctx.blobs.read(previous[0].blobs[GRIDDED]))
        written = await agent.feedback(
            experiment, passed, exif_checks, vision_checks, analysis, shot, previous, images
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
    experiment.verdicts.append(verdict)
    if passed:
        experiment.status = ExperimentStatus.COMPLETED
        experiment.closed_at = now()
    await repo.put_experiment(ctx.store, experiment)

    if not shot.experiment_id:
        shot.experiment_id = experiment.id
        await repo.put_shot(ctx.store, shot)

    await repo.record(
        ctx.store,
        shot.user_id,
        AGENT,
        "passed" if passed else "not_passed",
        {
            "technique_id": experiment.technique_id,
            "exif_checks": verdict.exif_checks,
            "vision_checks": {k: round(v, 2) for k, v in vision_checks.items()},
            "compared_with": previous[0].id if previous else "",
        },
        shot_id=shot.id,
        experiment_id=experiment.id,
    )
    await notify.verdict_given(ctx, experiment, verdict)
    if passed:
        await ctx.bus.publish(
            TOPICS["experiment.closed"], {"user_id": shot.user_id, "experiment_id": experiment.id}
        )


async def _previous_best(ctx: Context, shot, technique_id: str):
    """The earlier Shot of this Technique worth putting beside the new one.

    This used to pick the highest-scoring one, which quietly let a number
    nobody may see decide what "your previous best" means - the model's taste
    choosing the bar the photographer is measured against. The order now is:

    1. one the photographer marked a Keeper, because that is the only opinion
       here that is actually theirs (decision 45);
    2. failing that, the one the panel corroborated hardest, which is a claim
       about the Evidence rather than about the frame's worth;
    3. failing that, the most recent, which at least says "since then".

    The Technique Map remembers the Shot ids; the rest is a lookup.
    """
    skills = {s.technique_id: s for s in await repo.list_skills(ctx.store, shot.user_id)}
    state = skills.get(technique_id)
    if state is None:
        return None

    candidates = []
    for shot_id in state.shot_ids:
        if shot_id == shot.id:
            continue
        candidate = await repo.find_shot(ctx.store, shot_id)
        analysis = await repo.find_analysis(ctx.store, shot_id) if candidate else None
        if candidate is None or analysis is None:
            continue
        candidates.append((candidate, analysis))
    if not candidates:
        return None
    return max(candidates, key=lambda pair: _comparable_rank(pair, technique_id))


def _comparable_rank(pair, technique_id: str) -> tuple:
    """Keeper first, then how well the panel corroborated *this* technique in
    it, then recency. Never the frame's score."""
    candidate, analysis = pair
    evidence = next(
        (t for t in analysis.techniques if t.technique_id == technique_id), None
    )
    return (
        1 if candidate.kept_at else 0,
        evidence.agreement if evidence else 0,
        evidence.confidence if evidence else 0.0,
        candidate.captured_at or candidate.ingested_at,
    )
