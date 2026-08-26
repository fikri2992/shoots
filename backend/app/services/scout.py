"""Scout stage: issue the next experiment.

Triggered by the daily tick, by ``experiment.closed``, and by the dashboard's
"issue now" for demos. One open experiment per user (decision 6): if one is open
this is a no-op, so every trigger is safe to repeat.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.agents import scout as agent
from app.config import settings
from app.domain import scout as rules
from app.domain import taxonomy, technique_map, tendency, timing
from app.domain.entities import (
    Baseline,
    Change,
    ChangeState,
    Comparability,
    Experiment,
    ExperimentStatus,
    ExperimentTiming,
    ExperimentType,
    new_id,
    now,
)
from app.infra import repository as repo
from app.services import notify
from app.services import profile as profile_service
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "scout"
#: How many recent experiments' techniques are skipped when choosing the next one.
RECENT_EXPERIMENTS = 6


@dataclass(frozen=True)
class KeeperPattern:
    count: int
    reference_shot_id: str


async def issue(
    ctx: Context,
    user_id: str,
    force: bool = False,
    technique_id: str = "",
    requested_reason: str = "",
) -> Experiment | None:
    """Issue one experiment for the user if none is open. Returns it, or None.
    ``technique_id`` names the Technique (the Coach, by voice); otherwise the
    supported Direction chooses. With ``force`` the existing Experiment is
    skipped only after a replacement candidate is ready."""
    open_experiment = await repo.open_experiment(ctx.store, user_id)
    if open_experiment and not force:
        logger.info("scout: %s already has open experiment %s", user_id, open_experiment.id)
        return None

    states = {
        state.technique_id: state for state in await repo.list_technique_states(ctx.store, user_id)
    }

    recent = [
        q.technique_id
        for q in await repo.list_experiments(ctx.store, user_id, limit=RECENT_EXPERIMENTS)
    ]
    user = await repo.get_user(ctx.store, user_id)
    keeper_patterns = await _keeper_patterns(ctx, user_id)
    if technique_id:
        requested = taxonomy.BY_ID.get(technique_id)
        technique = (
            requested
            if requested
            and technique_id in keeper_patterns
            and rules.available(requested, missing_gear=user.constraints.missing_gear)
            else None
        )
    else:
        technique = rules.choose(
            tuple(keeper_patterns),
            recent,
            missing_gear=user.constraints.missing_gear,
        )
    if technique is None:
        reason = (
            "No marked Keeper has corroborated Technique Evidence yet."
            if not keeper_patterns
            else (
                "Every supported Keeper Technique was offered recently or conflicts "
                "with a constraint."
            )
        )
        await repo.record(
            ctx.store,
            user_id,
            AGENT,
            "nothing_to_issue",
            {"recent": recent, "reason": reason, "type": "reproduce"},
        )
        return None

    pattern = keeper_patterns[technique.id]
    count = pattern.count
    why = (
        f"{count} marked Keeper{'s' if count != 1 else ''} include {technique.name}; "
        "test whether you can make that decision deliberately."
    )
    critiques = await _recent_critiques(ctx, user_id)

    research = await agent.research(technique)
    out = await agent.write(
        technique,
        why,
        critiques,
        research,
        states,
        user.constraints,
        ExperimentType.REPRODUCE,
    )

    experiment = Experiment(
        id=new_id("experiment"),
        user_id=user_id,
        technique_id=technique.id,
        type=ExperimentType.REPRODUCE,
        title=out.title.strip()[:60] or technique.name,
        brief=agent.normalise_brief(out.brief)[:2000],
        why_now=(out.why_now.strip() or why)[:500],
        criteria=agent.criteria_for(technique, out.criteria_text),
        references=agent.pick_references(out, research),
        reference_shot_id=pattern.reference_shot_id,
        status=ExperimentStatus.OPEN,
        due_at=now() + timedelta(days=settings.experiment_ttl_days),
    )
    when = timing.deliver_at(technique.light, now(), user.last_latitude, user.last_longitude)
    experiment.deliver_at = when.at
    experiment.timing = ExperimentTiming(
        light=when.light, reason=when.reason, anchor=when.anchor, anchor_at=when.anchor_at
    )
    if open_experiment and force:
        await leave(ctx, user_id, open_experiment.id)
    if not await repo.create_open_experiment(ctx.store, experiment):
        logger.info("scout: %s lost the open Experiment claim", user_id)
        return None
    await repo.record(
        ctx.store,
        user_id,
        AGENT,
        "issued",
        {
            "technique_id": technique.id,
            "type": experiment.type.value,
            "title": experiment.title,
            "why": why,
            "selection_basis": "keeper",
            "reference_shot_id": experiment.reference_shot_id,
            "references": len(experiment.references),
            "hard_criteria": agent.hard_criteria_text(technique),
            "deliver_at": experiment.deliver_at.isoformat() if experiment.deliver_at else "",
            "timing": when.reason,
        },
        experiment_id=experiment.id,
    )
    await deliver_if_due(ctx, experiment)
    return experiment


async def _keeper_patterns(ctx: Context, user_id: str) -> dict[str, KeeperPattern]:
    """Corroborated Keeper Techniques with one fixed reference Shot each."""
    candidates: dict[str, list[tuple[str, int, float, datetime]]] = {}
    for shot in await repo.list_shots(ctx.store, user_id):
        if shot.kept_at is None:
            continue
        analysis = await repo.find_analysis(ctx.store, shot.id)
        if analysis is None:
            continue
        for evidence in analysis.techniques:
            if technique_map.corroborated(evidence):
                candidates.setdefault(evidence.technique_id, []).append(
                    (
                        shot.id,
                        evidence.agreement,
                        evidence.confidence,
                        shot.kept_at or shot.ingested_at,
                    )
                )
    patterns = {
        technique_id: KeeperPattern(
            count=len(rows),
            reference_shot_id=max(rows, key=lambda row: (row[1], row[2], row[3]))[0],
        )
        for technique_id, rows in candidates.items()
    }
    return dict(sorted(patterns.items(), key=lambda item: (-item[1].count, item[0])))


async def profile_for(ctx: Context, user_id: str) -> tendency.Profile:
    """The photographer's Tendency Profile, over everything stored.

    Pure arithmetic on measurements already on disk (``domain/tendency.py``):
    no model is called here.
    """
    return await profile_service.build(ctx, user_id)


def _snapshot(profile: tendency.Profile, source: str) -> dict[str, int]:
    """The counts an Experiment Direction was aimed at. Dwell has no buckets, so it is
    frozen as the two figures that make up its ratio."""
    if source == "dwell":
        return {"shots": profile.dwell.shots, "scenes": profile.dwell.scenes}
    found = profile.dimensions.get(source)
    return dict(found.counts) if found else {}


async def check_advice(ctx: Context, user_id: str) -> list[Experiment]:
    """Did comparable behaviour change after the Scout's own advice?

    Decision 37. Every closed Experiment that was aimed at a tendency is
    compared against where that tendency stands now — counts against counts, no
    model adjudicating — and the answer is written onto the Experiment Record.
    An agent that never checks its own recommendations is a critique queue, not
    a coach.

    Two things it refuses to say. It does not claim the Experiment *caused* the
    difference: it reports what the counts do, and the photographer can draw
    their own line between the two. And it does not claim the photographs got
    better — that stays the panel's opinion and is labelled as one.

    A Change that is only `insufficient evidence` because too little has been
    shot is left open and checked again; one that can never become comparable
    is written once and settled (``entities.Change.settled``).
    """
    profile = await profile_for(ctx, user_id)
    checked = []
    for experiment in await repo.list_experiments(ctx.store, user_id):
        if experiment.baseline is None or experiment.status is ExperimentStatus.OPEN:
            continue
        if experiment.change is not None and experiment.change.settled:
            continue
        change_profile = profile
        explicit_results: int | None = None
        if experiment.type is ExperimentType.REPRODUCE:
            selected = set(experiment.baseline.provenance.shot_ids)
            selected.update(experiment.result_shot_ids)
            change_profile = await profile_service.build_for_shots(ctx, user_id, selected)
            explicit_results = len(experiment.result_shot_ids)
        result = _change_for(
            experiment.baseline,
            change_profile,
            shots_since=explicit_results,
        )
        result.checked_at = now()
        experiment.change = result
        await repo.put_experiment(ctx.store, experiment)
        await repo.record(
            ctx.store,
            user_id,
            AGENT,
            "change_checked",
            {
                "technique_id": experiment.technique_id,
                "tendency": experiment.baseline.source,
                "state": result.state.value,
                "comparability": result.comparability.value,
                "outcome": result.outcome,
                "shots_since": result.added,
                "cited": experiment.baseline.citation,
            },
            experiment_id=experiment.id,
        )
        checked.append(experiment)
    return checked


def _change_for(
    baseline: Baseline,
    profile: tendency.Profile,
    *,
    shots_since: int | None = None,
) -> Change:
    """The Change for one frozen Baseline, or why there cannot be one.

    Both ways of being incomparable are recorded rather than skipped. A record
    that silently holds no Change reads as though nobody looked, which is the
    opposite of what happened.
    """
    if baseline.calc_version and baseline.calc_version != profile.calc_version:
        return Change(
            state=ChangeState.INSUFFICIENT,
            comparability=Comparability.DIFFERENT_ARITHMETIC,
            outcome=(
                f"measured by {baseline.calc_version}, and the profile now uses "
                f"{profile.calc_version} — the two do not compare"
            ),
        )
    baseline_ids = set(baseline.provenance.shot_ids)
    if not baseline_ids:
        return Change(
            state=ChangeState.INSUFFICIENT,
            comparability=Comparability.UNRECORDED_SAMPLE,
            outcome="this was set before the record kept what it was measured over",
        )
    current_ids = set(profile.shot_ids)
    missing = baseline_ids - current_ids
    if missing:
        return Change(
            state=ChangeState.INSUFFICIENT,
            comparability=Comparability.BASELINE_SHOTS_MISSING,
            outcome=f"{len(missing)} Baseline Shots are no longer in the archive",
        )
    if baseline.source == "dwell":
        return tendency.dwell_change(baseline.at_issue, profile.dwell)
    dimension = tendency.BY_ID.get(baseline.source)
    if dimension is None:
        return Change(
            state=ChangeState.INSUFFICIENT,
            comparability=Comparability.UNKNOWN_DIMENSION,
            outcome=f"nothing measures {baseline.source} any more",
        )
    if dimension.source == "model read":
        baseline_inputs = {(item.model, item.prompt_version) for item in baseline.provenance.inputs}
        current_versions = dict(profile.analysis_versions)
        baseline_reads_changed = any(
            current_versions.get(shot_id) != digest
            for shot_id, digest in baseline.provenance.analysis_versions.items()
        )
        if (
            not baseline.provenance.analysis_versions
            or baseline_inputs != set(profile.model_inputs)
            or baseline_reads_changed
        ):
            return Change(
                state=ChangeState.INSUFFICIENT,
                comparability=Comparability.DIFFERENT_MODEL_READING,
                outcome=(
                    "the Analyst model or prompt changed, so this model-read "
                    "dimension was re-baselined"
                ),
            )
    return tendency.change(
        dimension,
        baseline.at_issue,
        _snapshot(profile, baseline.source),
        shots_since=(len(current_ids - baseline_ids) if shots_since is None else shots_since),
    )


async def issue_first(ctx: Context, user_id: str) -> Experiment | None:
    """The first experiment, unprompted.

    A user who has just handed over their first Shots has nothing to do next,
    and waiting for tomorrow's tick to say so is the friction this whole thing
    exists to remove. Fires once, on an empty experiment history; after that the
    daily tick and ``experiment.closed`` are the only sources.
    """
    if await repo.list_experiments(ctx.store, user_id, limit=1):
        return None
    experiment = await issue(ctx, user_id)
    if experiment is not None:
        logger.info("scout: first experiment %s for %s", experiment.id, user_id)
    return experiment


async def consider_after_shot(ctx: Context, user_id: str, shot_id: str) -> str:
    """Plan from the updated record, or preserve an evidenced silence."""
    opened = await repo.open_experiment(ctx.store, user_id)
    if opened is not None:
        outcome = f'Existing Reproduce Experiment "{opened.title}" remains open.'
        await repo.record(
            ctx.store,
            user_id,
            AGENT,
            "held",
            {"reason": outcome, "type": opened.type.value},
            shot_id=shot_id,
            experiment_id=opened.id,
        )
        return outcome
    created = await issue(ctx, user_id)
    if created is not None:
        return f'Scout issued "{created.title}" from a marked Keeper.'
    return "Scout stayed silent because no supported Reproduce direction won."


async def deliver_if_due(ctx: Context, experiment: Experiment) -> bool:
    """Push the experiment if its moment has come. The experiment exists in the store
    either way; this is only about when the phone buzzes."""
    if experiment.delivered_at or experiment.status is not ExperimentStatus.OPEN:
        return False
    if experiment.deliver_at and experiment.deliver_at > now() + timing.SOON:
        return False
    await notify.experiment_issued(ctx, experiment)
    delivered_at = now()
    if not await repo.mark_experiment_delivered_if_open(ctx.store, experiment.id, delivered_at):
        return False
    await repo.record(
        ctx.store,
        experiment.user_id,
        AGENT,
        "delivered",
        {
            "technique_id": experiment.technique_id,
            "timing": experiment.timing.reason if experiment.timing else "",
        },
        experiment_id=experiment.id,
    )
    return True


async def deliver_due(ctx: Context) -> int:
    """The frequent tick: every open, undelivered experiment whose time has come."""
    delivered = 0
    for user in await repo.list_users(ctx.store):
        experiment = await repo.open_experiment(ctx.store, user.id)
        if experiment and await deliver_if_due(ctx, experiment):
            delivered += 1
    return delivered


async def skip(ctx: Context, user_id: str, experiment_id: str) -> Experiment:
    """The human gate. Logged, never deleted; the next tick issues another."""
    experiment = await repo.get_experiment(ctx.store, experiment_id)
    if experiment.user_id != user_id:
        raise repo.UnknownEntity(f"experiment {experiment_id}")
    if experiment.status is ExperimentStatus.OPEN:
        experiment, changed = await repo.transition_open_experiment(
            ctx.store, experiment.id, ExperimentStatus.SKIPPED, now()
        )
        if changed:
            await repo.release_open_experiment(ctx.store, user_id, experiment.id)
            await repo.record(
                ctx.store,
                user_id,
                "user",
                "skipped",
                {"technique_id": experiment.technique_id},
                experiment_id=experiment.id,
            )
    return experiment


async def leave(ctx: Context, user_id: str, experiment_id: str) -> Experiment:
    """End an open Experiment without grading the photographer's choice."""
    experiment = await repo.get_experiment(ctx.store, experiment_id)
    if experiment.user_id != user_id:
        raise repo.UnknownEntity(f"experiment {experiment_id}")
    if experiment.status is ExperimentStatus.OPEN:
        experiment, changed = await repo.transition_open_experiment(
            ctx.store, experiment.id, ExperimentStatus.LEFT, now()
        )
        if changed:
            await repo.release_open_experiment(ctx.store, user_id, experiment.id)
            await repo.record(
                ctx.store,
                user_id,
                "photographer",
                "left",
                {"technique_id": experiment.technique_id},
                experiment_id=experiment.id,
            )
    return experiment


async def expire(ctx: Context, user_id: str) -> list[Experiment]:
    """Open experiments past due become expired. Called by the daily tick.

    An expired Experiment says the offer ran out of time, and nothing at all
    about the Technique.
    """
    expired: list[Experiment] = []
    current = now()
    for experiment in await repo.list_experiments(ctx.store, user_id):
        overdue = experiment.due_at is not None and experiment.due_at < current
        if experiment.status is ExperimentStatus.OPEN and overdue:
            experiment, changed = await repo.transition_open_experiment(
                ctx.store, experiment.id, ExperimentStatus.EXPIRED, current
            )
            if not changed:
                continue
            await repo.release_open_experiment(ctx.store, user_id, experiment.id)
            await repo.record(
                ctx.store,
                user_id,
                "scheduler",
                "expired",
                {"technique_id": experiment.technique_id, "title": experiment.title},
                experiment_id=experiment.id,
            )
            expired.append(experiment)
    return expired


async def on_experiment_closed(ctx: Context, message: dict) -> str:
    # Judge and Cartographer consume media.analyzed independently. Judge may
    # close after Cartographer already looked for a closed Experiment, so the
    # close event owns the final check as well as the next plan.
    await check_advice(ctx, message["user_id"])
    from app.services import journey

    await journey.maybe_write(ctx, message["user_id"])
    created = await issue(ctx, message["user_id"])
    if created is not None:
        return f'Scout issued "{created.title}" after the Reproduce result settled.'
    return "Scout checked the settled result and stayed silent."


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
