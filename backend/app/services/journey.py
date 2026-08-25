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
from app.domain.entities import JourneyUpdate, Provenance, TechniqueStatus, new_id
from app.infra import repository as repo
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "journey"

#: Nothing is written below this many shots. A paragraph about who someone is
#: as a photographer needs a body of work, not a first afternoon.
MIN_SHOTS = 8

#: How much a dimension's exploration must move before it is worth a sentence.
#: Below this, the change is one shot's arithmetic and not a change in anybody.
MOVED_BY = 0.05

#: How many shots back to read. A tendency is about the whole body of work.
CORPUS = 500


async def profile_now(ctx: Context, user_id: str) -> tendency.Profile:
    shots = await repo.list_shots(ctx.store, user_id, limit=CORPUS)
    rows = [(shot, await repo.find_analysis(ctx.store, shot.id)) for shot in shots]
    keepers = {shot.id for shot in shots if shot.kept_at}
    return tendency.build(rows, keepers)


async def maybe_write(ctx: Context, user_id: str) -> JourneyUpdate | None:
    """Write the photographer's Journey Update if the profile has moved.

    Returns None when it has not, which is the common case and a real answer.
    """
    profile = await profile_now(ctx, user_id)
    if profile.shots < MIN_SHOTS:
        return None

    previous = await repo.latest_journey_update(ctx.store, user_id)
    since = _profile_at(previous)
    movements = [
        m
        for m in tendency.diff(since, profile)
        if abs(m.delta) >= MOVED_BY or m.newly_used
    ]
    skills = await repo.list_skills(ctx.store, user_id)
    solid = sorted(s.technique_id for s in skills if s.status is TechniqueStatus.RECURRING)
    fresh_solid = [t for t in solid if t not in (previous.became_solid if previous else [])]

    if previous is not None and not movements and not fresh_solid:
        return None

    # On a first update every bucket diffs against an empty profile, so every
    # one of them reads as newly used. That is arithmetic, not news, and
    # handing it to the writer as change would make the first paragraph a lie.
    evidence = _evidence(profile, movements if previous else [], fresh_solid)
    body = await agent.write(evidence, previous.body if previous else "", profile.taste_is_known)

    update = JourneyUpdate(
        id=new_id("journey"),
        user_id=user_id,
        body=body,
        evidence=evidence,
        widened=[m.dimension.id for m in movements if m.widened],
        counts={d.id: dict(profile.dimensions[d.id].counts) for d in tendency.DIMENSIONS},
        became_solid=solid,
        shots=profile.shots,
        taste_is_known=profile.taste_is_known,
        provenance=Provenance(
            shot_ids=list(profile.shot_ids),
            sample_size=profile.shots,
            calc_version=profile.calc_version,
            # Only where a model actually contributed language. A figures-only
            # update that lost its paragraph should not claim a model wrote it.
            model=settings.model_flash if body else "",
            prompt_version=prompts.version("journey") if body else "",
        ),
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
            "became_solid": fresh_solid,
            "evidence": len(evidence),
            "taste_is_known": profile.taste_is_known,
            "calc_version": profile.calc_version,
        },
    )
    return update


def _profile_at(previous: JourneyUpdate | None) -> tendency.Profile:
    """The profile the last update was written from, rebuilt from the counts it
    stored. An empty profile when there was no last update, so the first update
    reports everything as new — which, for the photographer, it is."""
    stored = previous.counts if previous else {}
    return tendency.Profile(
        dimensions={
            d.id: tendency.DimensionProfile(dimension=d, counts=dict(stored.get(d.id, {})))
            for d in tendency.DIMENSIONS
        },
        shots=previous.shots if previous else 0,
    )


def _evidence(
    profile: tendency.Profile,
    movements: list[tendency.Movement],
    fresh_solid: list[str],
) -> list[str]:
    """Every fact the writer is allowed to use, in plain sentences with their
    figures attached. Nothing about quality: the panel's score is not here, on
    purpose (decision 39)."""
    lines = [f"{profile.shots} shots read in total."]

    for dim in tendency.DIMENSIONS:
        p = profile.dimensions[dim.id]
        if not p.n:
            continue
        counts = ", ".join(f"{b} {p.counts[b]}" for b in dim.buckets if p.counts.get(b))
        line = f"{dim.label}: {counts} (of {p.n} readable)"
        if p.readable and p.narrow:
            line += f" — barely varies, {p.dominant_share:.0%} of them {p.dominant}"
        if p.readable and p.unexplored:
            line += f"; never {', '.join(p.unexplored)}"
        lines.append(line)

    dwell = profile.dwell
    if dwell.readable:
        lines.append(
            f"scenes: {dwell.shots} shots across {dwell.scenes} scenes, "
            f"{dwell.per_scene:.1f} frames each, longest {dwell.longest}"
            + (" — usually one frame and on" if dwell.walks_on else " — stays with a scene")
        )

    for movement in movements:
        direction = "widened" if movement.delta > 0 else "narrowed"
        line = f"{movement.dimension.label} {direction} since the last update"
        if movement.newly_used:
            line += f", first time shooting {', '.join(movement.newly_used)}"
        lines.append(line)

    if fresh_solid:
        names = ", ".join(t.replace("_", " ") for t in fresh_solid)
        # Said without the machinery: the writer is told not to mention lenses
        # or confidences, and it will happily repeat any that appear here.
        lines.append(f"now does reliably, seen and confirmed three separate times: {names}")

    if profile.taste_is_known:
        lines.append(f"{profile.keepers} shots marked as keepers by the photographer themselves.")
        for dim in tendency.DIMENSIONS:
            p = profile.dimensions[dim.id]
            for bucket in dim.buckets:
                lift = p.keeper_lift(bucket, profile.keeper_rate)
                if lift is not None and lift >= 1.5:
                    lines.append(
                        f"they keep {bucket} shots {lift:.1f} times as often as their average "
                        f"({dim.label})"
                    )
    else:
        lines.append(
            "the photographer has not marked enough keepers to say what they value — "
            "do not speak about taste"
        )

    for spot in profile.blind_spots:
        lines.append(f"cannot see: {spot}")
    return lines
