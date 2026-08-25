"""The Scout's gap finding: which Technique to ask for next. Pure.

Ranking, in order:

1. Only Techniques whose prerequisites have been observed (``unlocked``), plus
   any the record has not seen for a while and could offer again.
2. Not asked for recently (in the last ``recent`` ids).
3. Lowest level first: climb, do not jump.
4. Families the photographer has explored least come first, so the record
   fills out instead of going deep on one branch.
5. Catalogue order as the final tie-break, so the choice is deterministic.

Revisits come before new Techniques only when nothing at level 1 is open, so
someone still building breadth is never sent back over old ground first.

Staleness arrives as a set of ids rather than being read off a status
(``technique_map.stale_ids``). That is the whole difference decision 46 makes
here: the record says a Technique recurred and never un-says it, and whether
time has made it worth revisiting is this module's question to answer.
"""

from collections import Counter

from app.domain import taxonomy
from app.domain.entities import TechniqueState
from app.domain.taxonomy import Family, Technique
from app.domain.technique_map import observed_ids


def rank(
    skills: dict[str, TechniqueState],
    recent_technique_ids: list[str],
    video: bool = False,
    missing_gear: tuple[str, ...] | list[str] = (),
    stale: set[str] | frozenset[str] = frozenset(),
) -> list[Technique]:
    observed = observed_ids(skills)
    recent = set(recent_technique_ids)
    lacking = set(missing_gear)
    coverage = Counter(taxonomy.BY_ID[tid].family for tid in observed if tid in taxonomy.BY_ID)

    def possible(t: Technique) -> bool:
        return not (set(t.needs) & lacking)

    def offerable(t: Technique) -> bool:
        return t.id not in recent and (video or not t.video_only) and possible(t)

    fresh = [t for t in taxonomy.unlocked(observed) if offerable(t)]
    revisit = [
        taxonomy.BY_ID[tid]
        for tid in stale
        if tid in taxonomy.BY_ID and offerable(taxonomy.BY_ID[tid])
    ]

    order = {t.id: i for i, t in enumerate(taxonomy.TECHNIQUES)}

    def key(t: Technique) -> tuple:
        return (t.level, coverage.get(t.family, 0), order[t.id])

    fresh.sort(key=key)
    revisit.sort(key=key)

    has_level_one = any(t.level == 1 for t in fresh)
    return fresh + revisit if has_level_one else revisit + fresh


def choose(
    skills: dict[str, TechniqueState],
    recent_technique_ids: list[str],
    video: bool = False,
    missing_gear: tuple[str, ...] | list[str] = (),
    prefer: tuple[str, ...] | list[str] = (),
    stale: set[str] | frozenset[str] = frozenset(),
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
    ranked = rank(skills, recent_technique_ids, video, missing_gear, stale)
    if not ranked:
        return None
    wanted = list(prefer)
    if wanted:
        order = {tid: i for i, tid in enumerate(wanted)}
        ranked.sort(key=lambda t: order.get(t.id, len(order)))
    return ranked[0]


def why_now(
    technique: Technique,
    skills: dict[str, TechniqueState],
    stale: set[str] | frozenset[str] = frozenset(),
) -> str:
    """A plain sentence the card shows. The model may expand on it."""
    observed = observed_ids(skills)
    family_done = sum(
        1
        for tid in observed
        if tid in taxonomy.BY_ID and taxonomy.BY_ID[tid].family is technique.family
    )
    if technique.id in stale:
        return f"{technique.name} kept recurring in your work, and has not for a while."
    if technique.requires:
        names = ", ".join(taxonomy.BY_ID[r].name for r in technique.requires)
        return f"You have tried {names}; {technique.name} is the next step up."
    if family_done == 0:
        return f"Nothing in {technique.family.value} yet; this is the first door."
    return f"Level {technique.level} {technique.family.value}: fills out what you have started."


def family_coverage(skills: dict[str, TechniqueState]) -> dict[Family, int]:
    observed = observed_ids(skills)
    return {
        family: sum(1 for tid in observed if taxonomy.BY_ID[tid].family is family)
        for family in Family
    }
