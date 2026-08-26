"""Judge stage: ``media.analyzed`` → verdict on the open experiment → ``experiment.closed``.

Runs alongside the Cartographer on the same topic. Skips quietly when the
user has no open experiment or the shot is not a submission. A shot is judged
once: a second delivery finds its verdict already on the experiment.
"""

import logging
from datetime import datetime

from app.agents import judge as agent
from app.config import settings
from app.domain import judge as rules
from app.domain.entities import (
    Analysis,
    Experiment,
    ExperimentStatus,
    ExperimentType,
    Shot,
    Verdict,
    now,
)
from app.infra import repository as repo
from app.infra.bus import TOPICS
from app.infra.storage import GRIDDED
from app.services import notify
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "judge"


async def judge(ctx: Context, message: dict) -> str:
    """Judge if there is something to judge, then always publish ``media.judged``
    so the Scribe writes the review back with whatever verdict exists."""
    outcome = await _judge(ctx, message)
    await ctx.bus.publish(TOPICS["media.judged"], {"shot_id": message["shot_id"]})
    return outcome


async def _judge(ctx: Context, message: dict) -> str:
    shot = await repo.get_shot(ctx.store, message["shot_id"])
    if not shot.experiment_id:
        return "free Shot; no Experiment judgment"
    experiment = await repo.find_experiment(ctx.store, shot.experiment_id)
    if experiment is None or experiment.user_id != shot.user_id:
        return "associated Experiment is unavailable"
    if experiment.type is not ExperimentType.REPRODUCE:
        return f"{experiment.type.value} creates no Verdict"
    if not rules.is_submission(shot, experiment):
        return "Shot is not an explicit Reproduce result"
    if shot.id in experiment.result_shot_ids or any(
        verdict.shot_id == shot.id for verdict in experiment.verdicts
    ):
        logger.info("judge: %s already recorded for %s", shot.id, experiment.id)
        return "Reproduce result already recorded"
    if experiment.status is not ExperimentStatus.OPEN:
        return "Experiment settled before this result was read"

    analysis = await repo.find_analysis(ctx.store, shot.id)
    met, exif_checks, vision_checks = rules.evaluate(
        experiment.criteria, shot.exif, analysis, settings.judge_min_confidence
    )
    abstained = rules.abstention_reason(
        experiment.criteria,
        exif_checks,
        vision_checks,
        analysis,
        settings.judge_min_confidence,
    )
    if abstained:
        _, recorded = await repo.record_reproduce_result_if_open(
            ctx.store, experiment.id, shot.id, None, now()
        )
        if not recorded:
            return "Experiment settled before abstention was recorded"
        await repo.record(
            ctx.store,
            shot.user_id,
            AGENT,
            "abstained",
            {
                "technique_id": experiment.technique_id,
                "reason": abstained,
                "exif_checks": exif_checks,
                "vision_checks": {key: round(value, 2) for key, value in vision_checks.items()},
            },
            shot_id=shot.id,
            experiment_id=experiment.id,
        )
        return "Judge abstained; no Verdict"

    previous = await _previous_best(ctx, shot, experiment)
    try:
        images = [await ctx.blobs.read(shot.blobs[GRIDDED])] if GRIDDED in shot.blobs else []
        if previous and GRIDDED in previous[0].blobs and images:
            images.append(await ctx.blobs.read(previous[0].blobs[GRIDDED]))
        written = await agent.feedback(
            experiment, met, exif_checks, vision_checks, analysis, shot, previous, images
        )
        text = written.feedback.strip()
        if written.tip.strip():
            text = f"{text}\n\nNext: {written.tip.strip()}"
    except Exception:  # the verdict must land even if the model does not
        logger.exception("judge: feedback model failed for %s", shot.id)
        lines = rules.describe_checks(exif_checks, vision_checks, settings.judge_min_confidence)
        text = ("Criteria met. " if met else "Not yet. ") + "; ".join(lines)

    verdict = Verdict(
        shot_id=shot.id,
        criteria_met=met,
        exif_checks={k: (None if v is None else bool(v)) for k, v in exif_checks.items()},
        vision_checks=vision_checks,
        feedback=text[:2000],
        compared_with=previous[0].id if previous else "",
    )
    experiment, recorded = await repo.record_reproduce_result_if_open(
        ctx.store, experiment.id, shot.id, verdict, now()
    )
    if not recorded:
        logger.info("judge: %s lost the Experiment transition", shot.id)
        return "Experiment settled before Verdict was recorded"
    if met:
        await repo.release_open_experiment(ctx.store, shot.user_id, experiment.id)

    await repo.record(
        ctx.store,
        shot.user_id,
        AGENT,
        "criteria_met" if met else "criteria_not_met",
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
    if met:
        await ctx.bus.publish(
            TOPICS["experiment.closed"],
            {
                "user_id": shot.user_id,
                "experiment_id": experiment.id,
                "shot_id": shot.id,
            },
        )
    return "Reproduce Criteria met" if met else "Reproduce Criteria not met"


async def _previous_best(
    ctx: Context, shot: Shot, experiment: Experiment
) -> tuple[Shot, Analysis] | None:
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
    technique_id = experiment.technique_id
    if experiment.reference_shot_id and experiment.reference_shot_id != shot.id:
        reference = await repo.find_shot(ctx.store, experiment.reference_shot_id)
        reference_analysis = (
            await repo.find_analysis(ctx.store, experiment.reference_shot_id) if reference else None
        )
        if reference is not None and reference_analysis is not None:
            return reference, reference_analysis

    states = {
        state.technique_id: state
        for state in await repo.list_technique_states(ctx.store, shot.user_id)
    }
    state = states.get(technique_id)
    if state is None:
        return None

    candidates: list[tuple[Shot, Analysis]] = []
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


def _comparable_rank(
    pair: tuple[Shot, Analysis], technique_id: str
) -> tuple[int, int, float, datetime]:
    """Keeper first, then how well the panel corroborated *this* technique in
    it, then recency. Never the frame's score."""
    candidate, analysis = pair
    evidence = next((t for t in analysis.techniques if t.technique_id == technique_id), None)
    return (
        1 if candidate.kept_at else 0,
        evidence.agreement if evidence else 0,
        evidence.confidence if evidence else 0.0,
        candidate.captured_at or candidate.ingested_at,
    )
