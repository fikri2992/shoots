"""The Scout's gap finding: which technique to ask for next. Pure.

Ranking, in order:

1. Only techniques whose prerequisites are at least attempted (``unlocked``),
   plus rusty ones, which are worth a refresher.
2. Not issued recently (a quest on it in the last ``recent`` ids).
3. Lowest level first: climb, do not jump.
4. Families the photographer has explored least come first, so the map
   fills out instead of going deep on one branch.
5. Catalogue order as the final tie-break, so the choice is deterministic.

Rusty techniques come before new ones only when nothing at level 1 is open,
so a beginner is never sent to re-polish before they have breadth.
"""

from collections import Counter

from app.domain import taxonomy
from app.domain.entities import SkillState, SkillStatus
from app.domain.skills import attempted_ids
from app.domain.taxonomy import Family, Technique


def rank(
    skills: dict[str, SkillState],
    recent_technique_ids: list[str],
    video: bool = False,
    missing_gear: tuple[str, ...] | list[str] = (),
) -> list[Technique]:
    attempted = attempted_ids(skills)
    recent = set(recent_technique_ids)
    lacking = set(missing_gear)
    coverage = Counter(taxonomy.BY_ID[tid].family for tid in attempted if tid in taxonomy.BY_ID)

    def possible(t: Technique) -> bool:
        return not (set(t.needs) & lacking)

    fresh = [
        t
        for t in taxonomy.unlocked(attempted)
        if t.id not in recent and (video or not t.video_only) and possible(t)
    ]
    rusty = [
        taxonomy.BY_ID[tid]
        for tid, s in skills.items()
        if s.status is SkillStatus.RUSTY
        and tid not in recent
        and tid in taxonomy.BY_ID
        and possible(taxonomy.BY_ID[tid])
    ]

    order = {t.id: i for i, t in enumerate(taxonomy.TECHNIQUES)}

    def key(t: Technique) -> tuple:
        return (t.level, coverage.get(t.family, 0), order[t.id])

    fresh.sort(key=key)
    rusty.sort(key=key)

    has_level_one = any(t.level == 1 for t in fresh)
    return fresh + rusty if has_level_one else rusty + fresh


def choose(
    skills: dict[str, SkillState],
    recent_technique_ids: list[str],
    video: bool = False,
    missing_gear: tuple[str, ...] | list[str] = (),
    prefer: tuple[str, ...] | list[str] = (),
) -> Technique | None:
    """The next technique to ask for.

    ``prefer`` is what the Tendency Profile suggests would push against the
    photographer's own narrowest dimension (``domain/tendency.py``). It reorders
    the ranking; it never widens it. A preferred technique whose prerequisites
    are unmet, which was asked for recently, or which needs gear the
    photographer does not have, is not in ``rank``'s output and so cannot be
    chosen here — the curriculum still decides what is *possible*, and the
    profile only decides what is *interesting* among those.
    """
    ranked = rank(skills, recent_technique_ids, video, missing_gear)
    if not ranked:
        return None
    wanted = list(prefer)
    if wanted:
        order = {tid: i for i, tid in enumerate(wanted)}
        ranked.sort(key=lambda t: order.get(t.id, len(order)))
    return ranked[0]


def why_now(technique: Technique, skills: dict[str, SkillState]) -> str:
    """A plain sentence the quest card shows. The model may expand on it."""
    state = skills.get(technique.id)
    attempted = attempted_ids(skills)
    family_done = sum(
        1
        for tid in attempted
        if tid in taxonomy.BY_ID and taxonomy.BY_ID[tid].family is technique.family
    )
    if state and state.status is SkillStatus.RUSTY:
        return f"You had {technique.name} solid and have not practised it in a while."
    if technique.requires:
        names = ", ".join(taxonomy.BY_ID[r].name for r in technique.requires)
        return f"You have tried {names}; {technique.name} is the next step up."
    if family_done == 0:
        return f"Nothing in {technique.family.value} yet; this is the first door."
    return f"Level {technique.level} {technique.family.value}: fills out what you have started."


def family_coverage(skills: dict[str, SkillState]) -> dict[Family, int]:
    attempted = attempted_ids(skills)
    return {
        family: sum(1 for tid in attempted if taxonomy.BY_ID[tid].family is family)
        for family in Family
    }
