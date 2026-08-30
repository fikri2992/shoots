"""Journey stage: has enough changed to say something, and what can be said?

The decision is arithmetic and the prose is a model's — the same division as
everywhere else. ``domain/tendency.py`` diffs the profile against the one the
last update was written from; if nothing moved, nothing is written, because an
update that arrives on a schedule with nothing behind it is exactly the
engagement-shaped noise this product refuses to be.

What the evidence may contain is bounded here rather than in the prompt: the
writer can only say what this function hands it.
"""

import logging

from app.agents import journey as agent
from app.agents import prompts
from app.config import settings
from app.domain import tendency
from app.domain.entities import (
    ChangeState,
    Experiment,
    ExperimentStatus,
    JourneyUpdate,
    TechniqueStatus,
    new_id,
)
from app.infra import repository as repo
from app.services import profile as profile_service
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "journey"

#: Nothing is written below this many shots. A paragraph about who someone is
#: as a photographer needs a body of work, not a first afternoon.
MIN_SHOTS = 8

#: How much a dimension's exploration must move before it is worth a sentence.
#: Below this, the change is one shot's arithmetic and not a change in anybody.
MOVED_BY = 0.05


async def profile_now(ctx: Context, user_id: str) -> tendency.Profile:
    return await profile_service.build(ctx, user_id)


async def maybe_write(ctx: Context, user_id: str) -> JourneyUpdate | None:
    """Write the photographer's Journey Update if the profile has moved.

    Returns None when it has not, which is the common case and a real answer.
    """
    profile = await profile_now(ctx, user_id)
    if profile.shots < MIN_SHOTS:
        return None

    previous = await repo.latest_journey_update(ctx.store, user_id)
    # A profile built by different arithmetic is not a baseline for this one.
    # Move a bucket edge and the same photographs re-bucket wholesale: every
    # dimension clears MOVED_BY, unused buckets fill, and the paragraph reports
    # a week of change to a photographer who did not pick up a camera. So the
    # last update stops counting as a comparison, and this one re-baselines
    # instead - which is why the write is not suppressed below when it cannot
    # compare, or the profile would be stuck against a baseline it can never
    # legitimately diff.
    current_ids = set(profile.shot_ids)
    current_analysis_versions = dict(profile.analysis_versions)
    previous_reads_unchanged = bool(previous and previous.provenance.analysis_versions) and all(
        current_analysis_versions.get(shot_id) == digest
        for shot_id, digest in (previous.provenance.analysis_versions.items() if previous else ())
    )
    comparable = (
        previous is not None
        and previous.provenance.calc_version == profile.calc_version
        and bool(previous.provenance.shot_ids)
        and set(previous.provenance.shot_ids) <= current_ids
        and previous_reads_unchanged
        and {(item.model, item.prompt_version) for item in previous.provenance.inputs}
        == set(profile.model_inputs)
    )
    since = _profile_at(previous if comparable else None)
    movements = (
        [m for m in tendency.diff(since, profile) if abs(m.delta) >= MOVED_BY or m.newly_used]
        if comparable
        else []
    )
    states = await repo.list_technique_states(ctx.store, user_id)
    recurring = sorted(
        state.technique_id for state in states if state.status is TechniqueStatus.RECURRING
    )
    # Technique ids do not depend on the arithmetic, so this half stays a fair
    # comparison even when the counts do not.
    fresh = [t for t in recurring if t not in (previous.became_recurring if previous else [])]
    retracted = sorted(set(previous.became_recurring if previous else []) - set(recurring))
    keeper_counts = {
        dimension.id: dict(profile.dimensions[dimension.id].keepers)
        for dimension in tendency.DIMENSIONS
    }
    keeper_changed = previous is not None and (
        previous.keepers != profile.keepers or previous.keeper_counts != keeper_counts
    )
    meaningful_keeper_change = keeper_changed and (
        profile.taste_is_known or bool(previous and previous.taste_is_known)
    )

    if (
        comparable
        and not movements
        and not fresh
        and not retracted
        and not meaningful_keeper_change
    ):
        return None

    # On a first update every bucket diffs against an empty profile, so every
    # one of them reads as newly used. That is arithmetic, not news, and
    # handing it to the writer as change would make the first paragraph a lie.
    evidence = _evidence(
        profile,
        movements,
        fresh,
        await _last_change(ctx, user_id),
        retracted_recurring=retracted,
    )
    body = (
        _correction_body(retracted)
        if retracted
        else await agent.write(evidence, previous.body if previous else "", profile.taste_is_known)
    )

    provenance = profile_service.provenance(profile)
    provenance.model = settings.model_flash if body and not retracted else ""
    provenance.prompt_version = prompts.version("journey") if body and not retracted else ""
    update = JourneyUpdate(
        id=new_id("journey"),
        user_id=user_id,
        body=body,
        evidence=evidence,
        widened=[m.dimension.id for m in movements if m.widened],
        counts={d.id: dict(profile.dimensions[d.id].counts) for d in tendency.DIMENSIONS},
        became_recurring=recurring,
        shots=profile.shots,
        taste_is_known=profile.taste_is_known,
        keepers=profile.keepers,
        keeper_counts=keeper_counts,
        provenance=provenance,
    )
    await repo.put_journey_update(ctx.store, update)
    await repo.record(
        ctx.store,
        user_id,
        AGENT,
        "updated",
        {
            "shots": profile.shots,
            "widened": update.widened,
            "became_recurring": fresh,
            "retracted_recurring": retracted,
            "evidence": len(evidence),
            "taste_is_known": profile.taste_is_known,
            "keepers": profile.keepers,
            "calc_version": profile.calc_version,
        },
    )
    return update


def _profile_at(previous: JourneyUpdate | None) -> tendency.Profile:
    """The profile the last update was written from, rebuilt from the counts it
    stored. An empty profile when there was no last update, so the first update
    reports everything as new — which, for the photographer, it is.

    ``calc_version`` is carried over rather than left to default, so the
    rebuilt profile says which arithmetic produced it. Defaulting would make it
    claim the current version and any comparison against it would pass
    vacuously.
    """
    stored = previous.counts if previous else {}
    return tendency.Profile(
        dimensions={
            d.id: tendency.DimensionProfile(dimension=d, counts=dict(stored.get(d.id, {})))
            for d in tendency.DIMENSIONS
        },
        shots=previous.shots if previous else 0,
        calc_version=previous.provenance.calc_version if previous else "",
    )


async def _last_change(ctx: Context, user_id: str) -> Experiment | None:
    """The most recent closed Experiment whose Change could actually be
    measured. Anything the arithmetic declined to compare is left out: the
    paragraph is written from figures, and `insufficient evidence` is the
    absence of one."""
    for experiment in await repo.list_experiments(
        ctx.store, user_id, limit=settings.journey_experiments_back
    ):
        change = experiment.change
        if experiment.status is ExperimentStatus.OPEN or experiment.baseline is None:
            continue
        if change is not None and change.state is not ChangeState.INSUFFICIENT:
            return experiment
    return None


def _evidence(
    profile: tendency.Profile,
    movements: list[tendency.Movement],
    fresh_recurring: list[str],
    last_change: Experiment | None = None,
    *,
    retracted_recurring: list[str] | None = None,
) -> list[str]:
    """Every fact the writer is allowed to use, in plain sentences with their
    figures attached. Nothing about quality: the panel's score is not here, on
    purpose (decision 39)."""
    lines = [f"Shoots read {profile.shots} Shots."]

    for dim in tendency.DIMENSIONS:
        p = profile.dimensions[dim.id]
        if not p.n:
            continue
        counts = ", ".join(f"{p.counts[b]} {b}" for b in dim.buckets if p.counts.get(b))
        authority = "visually read" if dim.source == "model read" else "measured"
        line = f"For {dim.label}, Shoots {authority} {counts} across {p.n} readable Shots."
        if p.readable and p.narrow:
            line += f" {p.dominant.capitalize()} appears in {p.counts[p.dominant]} of them."
        if p.readable and p.never_used:
            line += f" None are {', '.join(p.never_used)} yet."
        lines.append(line)

    dwell = profile.dwell
    if dwell.readable:
        lines.append(
            f"You made {dwell.shots} Shots across {dwell.scenes} Scenes, averaging "
            f"{dwell.per_scene:.1f} per Scene. The longest Scene has {dwell.longest} Shots."
        )

    for movement in movements:
        direction = "spread wider" if movement.delta > 0 else "became more consistent"
        line = f"Since the last update, {movement.dimension.label} {direction}."
        if movement.newly_used:
            line += f" {', '.join(movement.newly_used).capitalize()} appears for the first time."
        lines.append(line)

    if fresh_recurring:
        names = ", ".join(t.replace("_", " ") for t in fresh_recurring)
        # Said without the machinery: the writer is told not to mention lenses
        # or confidences, and it will happily repeat any that appear here.
        lines.append(
            f"Shoots' visual reads find {names} in at least three separate Shots. "
            "It keeps returning, but has not been tested on purpose."
        )

    if retracted_recurring:
        names = ", ".join(t.replace("_", " ") for t in retracted_recurring)
        lines.append(
            f"Shoots corrected an earlier label for {names}. The current visual-read "
            "counts no longer reach the recurring threshold."
        )

    # Two facts side by side, never joined: what they were offered, and what
    # their counts did afterwards. The prompt forbids the word between them,
    # because nothing here can tell a followed suggestion from a coincidence.
    if last_change is not None and last_change.baseline is not None:
        technique = last_change.technique_id.replace("_", " ")
        lines.append(
            f"Shoots offered {technique} as an Experiment. {last_change.baseline.citation}"
        )
        lines.append(last_change.change.outcome)

    if profile.taste_is_known:
        lines.append(f"You marked {profile.keepers} Shots as Keepers.")
        for dim in tendency.DIMENSIONS:
            p = profile.dimensions[dim.id]
            if p.readable_keepers < tendency.MIN_KEEPERS_FOR_TASTE:
                continue
            for bucket in dim.buckets:
                marked = p.keepers.get(bucket, 0)
                if marked:
                    lines.append(
                        f"{marked} of {p.readable_keepers} readable Keepers are {bucket} "
                        f"for {dim.label}."
                    )
    else:
        lines.append(
            f"You marked {profile.keepers} Shots as Keepers. With "
            f"{tendency.MIN_KEEPERS_FOR_TASTE}, Shoots can start finding where those "
            "choices gather."
        )

    for spot in profile.blind_spots:
        lines.append(f"Still unclear: {spot}.")
    return lines


def _correction_body(retracted: list[str]) -> str:
    """Code-authored correction when Shoots' earlier label was too strong."""
    examples = ", ".join(item.replace("_", " ") for item in retracted[:3])
    more = f", and {len(retracted) - 3} others" if len(retracted) > 3 else ""
    return (
        f"Shoots corrected an earlier label for {examples}{more}. Those Techniques no longer "
        "reach the current recurring threshold. The sightings are still here. The earlier label, "
        "not your photography, was wrong."
    )
