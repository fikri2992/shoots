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
from app.domain import explore, taxonomy, technique_map, tendency, timing
from app.domain import scout as rules
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
from app.infra.bus import TOPICS
from app.services import notify, photographer_memory
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
    shot_ids: tuple[str, ...]


async def issue(
    ctx: Context,
    user_id: str,
    force: bool = False,
    technique_id: str = "",
    requested_reason: str = "",
    experiment_id: str = "",
) -> Experiment | None:
    """Issue one experiment for the user if none is open. Returns it, or None.
    ``technique_id`` names an explicitly requested Technique; otherwise a supported
    Direction chooses. With ``force`` the existing Experiment is skipped only after
    a replacement candidate is ready."""
    if experiment_id:
        recovered = await repo.find_experiment(ctx.store, experiment_id)
        if recovered is not None:
            if recovered.user_id != user_id:
                raise repo.UnknownEntity(f"experiment {experiment_id}")
            return recovered
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
    constraints = await photographer_memory.constraints_for(
        ctx,
        user_id,
        role="scout",
        purpose="experiment_selection",
    )
    patterns = await keeper_patterns(ctx, user_id)
    if technique_id:
        requested = taxonomy.BY_ID.get(technique_id)
        technique = (
            requested
            if requested
            and technique_id in patterns
            and rules.available(requested, missing_gear=constraints.missing_gear)
            else None
        )
    else:
        technique = rules.choose(
            tuple(patterns),
            recent,
            missing_gear=constraints.missing_gear,
        )
    if technique is None:
        reason = (
            "No marked Keeper has a Technique that appears clearly enough to repeat yet."
            if not patterns
            else (
                "Every supported Keeper Technique was offered recently or does not fit "
                "a saved constraint."
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

    pattern = patterns[technique.id]
    count = pattern.count
    why = (
        f"You marked {count} Shot{'s' if count != 1 else ''} with {technique.name} as "
        f"{'Keepers' if count != 1 else 'a Keeper'}. Try making that choice again on purpose."
    )
    critiques = await _recent_critiques(ctx, user_id)

    research = await agent.research(technique)
    out = await agent.write(
        technique,
        why,
        critiques,
        research,
        states,
        constraints,
        ExperimentType.REPRODUCE,
    )

    experiment = Experiment(
        id=experiment_id or new_id("experiment"),
        user_id=user_id,
        technique_id=technique.id,
        type=ExperimentType.REPRODUCE,
        title=out.title.strip()[:60] or technique.name,
        brief=agent.normalise_brief(out.brief)[:2000],
        why_now=(out.why_now.strip() or why)[:500],
        criteria=agent.criteria_for(technique, out.criteria_text),
        references=agent.pick_references(out, research),
        reference_shot_id=pattern.reference_shot_id,
        warrant_shot_ids=list(pattern.shot_ids),
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
            "selection_basis": "explicit_request" if technique_id else "keeper",
            "requested_reason": requested_reason.strip() if technique_id else "",
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


async def keeper_patterns(ctx: Context, user_id: str) -> dict[str, KeeperPattern]:
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
            shot_ids=tuple(sorted(row[0] for row in rows)),
        )
        for technique_id, rows in candidates.items()
    }
    return dict(sorted(patterns.items(), key=lambda item: (-item[1].count, item[0])))


async def issue_explore(
    ctx: Context,
    user_id: str,
    *,
    force: bool = False,
    technique_id: str = "",
    requested_reason: str = "",
    experiment_id: str = "",
    warrant_shot_ids: list[str] | None = None,
    selection_basis: str = "",
    exclude_technique_ids: set[str] | None = None,
) -> Experiment | None:
    """Offer optional Variations from a Tendency Direction or explicit Technique."""
    opened = await repo.open_experiment(ctx.store, user_id)
    if opened is not None and not force:
        return None
    experiment = await plan_explore(
        ctx,
        user_id,
        technique_id=technique_id,
        requested_reason=requested_reason,
        experiment_id=experiment_id,
        warrant_shot_ids=warrant_shot_ids,
        exclude_technique_ids=exclude_technique_ids,
    )
    if experiment is None:
        recent = [
            item.technique_id
            for item in await repo.list_experiments(ctx.store, user_id, limit=RECENT_EXPERIMENTS)
        ]
        await repo.record(
            ctx.store,
            user_id,
            AGENT,
            "nothing_to_issue",
            {
                "recent": recent,
                "reason": "No supported Tendency Direction is available for Explore.",
                "type": "explore",
            },
        )
        return None
    if opened is not None and force:
        await leave(ctx, user_id, opened.id)
    if not await repo.create_open_experiment(ctx.store, experiment):
        return None
    await repo.record(
        ctx.store,
        user_id,
        AGENT,
        "issued",
        {
            "technique_id": experiment.technique_id,
            "type": "explore",
            "title": experiment.title,
            "why": experiment.why_now,
            "selection_basis": selection_basis
            or ("tendency" if experiment.baseline else "explicit_request"),
            "variations": [variation.id for variation in experiment.variations],
            "deliver_at": experiment.deliver_at.isoformat() if experiment.deliver_at else "",
        },
        experiment_id=experiment.id,
    )
    await deliver_if_due(ctx, experiment)
    return experiment


async def plan_explore(
    ctx: Context,
    user_id: str,
    *,
    technique_id: str = "",
    requested_reason: str = "",
    experiment_id: str = "",
    warrant_shot_ids: list[str] | None = None,
    exclude_technique_ids: set[str] | None = None,
) -> Experiment | None:
    """Prepare a supported Explore without storing or opening it."""
    profile = await profile_for(ctx, user_id)
    direction = tendency.direction_for(profile)
    recent = [
        item.technique_id
        for item in await repo.list_experiments(ctx.store, user_id, limit=RECENT_EXPERIMENTS)
    ]
    if not technique_id:
        recent.extend(sorted(exclude_technique_ids or set()))
    constraints = await photographer_memory.constraints_for(
        ctx,
        user_id,
        role="scout",
        purpose="experiment_selection",
    )
    if technique_id:
        requested = taxonomy.BY_ID.get(technique_id)
        technique = (
            requested
            if requested and rules.available(requested, missing_gear=constraints.missing_gear)
            else None
        )
    else:
        technique = (
            rules.choose(
                direction.prefers,
                recent,
                missing_gear=constraints.missing_gear,
            )
            if direction is not None
            else None
        )
    if technique is None:
        return None

    supported_direction = direction is not None and technique.id in direction.prefers
    why = (
        rules.why_now(technique, direction.citation)
        if supported_direction and direction is not None
        else requested_reason.strip()
        or f"You asked to explore {technique.name} without grading the result."
    )
    baseline = (
        Baseline(
            source=direction.source,
            citation=direction.citation,
            at_issue=_snapshot(profile, direction.source),
            calc_version=profile.calc_version,
            provenance=profile_service.provenance(profile),
        )
        if supported_direction and direction is not None
        else None
    )
    user = await repo.get_user(ctx.store, user_id)
    at = now()
    when = timing.deliver_at(technique.light, at, user.last_latitude, user.last_longitude)
    experiment = Experiment(
        id=experiment_id or new_id("experiment"),
        user_id=user_id,
        technique_id=technique.id,
        type=ExperimentType.EXPLORE,
        title=f"Explore {technique.name}",
        brief="Pick the version that makes you curious. Try another only if you want to compare.",
        why_now=why[:500],
        variations=explore.variations_for(technique),
        baseline=baseline,
        warrant_shot_ids=(
            list(baseline.provenance.shot_ids) if baseline else list(warrant_shot_ids or [])
        ),
        status=ExperimentStatus.OPEN,
        due_at=at + timedelta(days=settings.experiment_ttl_days),
        deliver_at=when.at,
        timing=ExperimentTiming(
            light=when.light,
            reason=when.reason,
            anchor=when.anchor,
            anchor_at=when.anchor_at,
        ),
    )
    return experiment


async def complete_explore(ctx: Context, user_id: str, experiment_id: str) -> Experiment:
    """End an Explore after at least one explicit result, without a Verdict."""
    experiment = await repo.get_experiment(ctx.store, experiment_id)
    if experiment.user_id != user_id:
        raise repo.UnknownEntity(f"experiment {experiment_id}")
    if experiment.type is not ExperimentType.EXPLORE:
        raise ValueError("Only Explore is completed by the Photographer")
    if not experiment.result_shot_ids:
        raise ValueError("Try at least one Variation, or leave the Experiment")
    active = await repo.active_capture_session(ctx.store, experiment.id)
    if active is not None and active.status.value not in {"settled", "cancelled", "expired"}:
        raise ValueError("Finish the active Capture Session first")
    experiment, changed = await repo.transition_open_experiment(
        ctx.store,
        experiment.id,
        ExperimentStatus.COMPLETED,
        now(),
    )
    if changed:
        await repo.release_open_experiment(ctx.store, user_id, experiment.id)
        await repo.record(
            ctx.store,
            user_id,
            "photographer",
            "explore_completed",
            {
                "results": len(experiment.result_shot_ids),
                "variations_tried": len(
                    {item.variation_id for item in experiment.variation_observations}
                ),
                "verdicts": 0,
            },
            experiment_id=experiment.id,
        )
        await ctx.bus.publish(
            TOPICS["experiment.closed"],
            {
                "user_id": user_id,
                "experiment_id": experiment.id,
                "shot_id": experiment.result_shot_ids[-1],
            },
        )
    return experiment


async def _keeper_patterns(ctx: Context, user_id: str) -> dict[str, KeeperPattern]:
    """Compatibility seam for older callers; new code uses ``keeper_patterns``."""
    return await keeper_patterns(ctx, user_id)


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
        if experiment.type in {ExperimentType.REPRODUCE, ExperimentType.EXPLORE}:
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
                "Shoots changed how it calculates this pattern, so the old and new "
                "numbers cannot be compared."
            ),
        )
    baseline_ids = set(baseline.provenance.shot_ids)
    if not baseline_ids:
        return Change(
            state=ChangeState.INSUFFICIENT,
            comparability=Comparability.UNRECORDED_SAMPLE,
            outcome=(
                "Shoots did not keep the original comparison group, so it cannot "
                "compare this fairly."
            ),
        )
    current_ids = set(profile.shot_ids)
    missing = baseline_ids - current_ids
    if missing:
        return Change(
            state=ChangeState.INSUFFICIENT,
            comparability=Comparability.BASELINE_SHOTS_MISSING,
            outcome=(
                f"{len(missing)} {'Shot is' if len(missing) == 1 else 'Shots are'} missing from "
                "the original comparison, so Shoots stopped here."
            ),
        )
    if baseline.source == "dwell":
        return tendency.dwell_change(baseline.at_issue, profile.dwell)
    dimension = tendency.BY_ID.get(baseline.source)
    if dimension is None:
        return Change(
            state=ChangeState.INSUFFICIENT,
            comparability=Comparability.UNKNOWN_DIMENSION,
            outcome=(
                f"Shoots no longer reads {baseline.source}, so this comparison cannot continue."
            ),
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
                    "Shoots changed how it visually reads this pattern, so it started "
                    "a fresh comparison."
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
    """Settle the per-Shot Run without choosing the Shoot intervention early."""
    opened = await repo.open_experiment(ctx.store, user_id)
    if opened is not None:
        outcome = f'Your Experiment "{opened.title}" is still open.'
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
    outcome = "Shoots will look across the whole outing before suggesting anything."
    await repo.record(
        ctx.store,
        user_id,
        AGENT,
        "shoot_decision_deferred",
        {"reason": outcome},
        shot_id=shot_id,
    )
    return outcome


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
    for user in await repo.list_writable_users(ctx.store):
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
            from app.services import interventions

            await interventions.refresh_for_experiment(ctx, experiment.id)
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
            from app.services import interventions

            await interventions.refresh_for_experiment(ctx, experiment.id)
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
            from app.services import interventions

            await interventions.refresh_for_experiment(ctx, experiment.id)
            expired.append(experiment)
    return expired


async def on_experiment_closed(ctx: Context, message: dict) -> str:
    # Judge and Cartographer consume media.analyzed independently. Judge may
    # close after Cartographer already looked for a closed Experiment, so the
    # close event owns the final check as well as the next plan.
    from app.services import cartographer, journey

    await cartographer.rebuild(ctx, message["user_id"])
    await check_advice(ctx, message["user_id"])
    from app.services import deconstructions, interventions

    await interventions.refresh_for_experiment(ctx, message["experiment_id"])
    experiment = await repo.get_experiment(ctx.store, message["experiment_id"])
    if experiment.result_shot_ids:
        try:
            await deconstructions.prepare_experiment_record(ctx, experiment)
        except Exception:  # noqa: BLE001 - Experiment closure remains authoritative
            logger.exception(
                "preparing Deconstruction for Experiment %s failed",
                experiment.id,
            )
    await journey.maybe_write(ctx, message["user_id"])
    created = await issue(ctx, message["user_id"])
    if created is not None:
        return f'Shoots prepared "{created.title}" after reading the Experiment result.'
    return "Shoots checked the result and found no useful next idea."


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
