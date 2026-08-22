"""The Cartographer's rules: how evidence moves a technique through the graph.

Pure functions over ``SkillState``. Reproducible from stored analyses, which
is the point: a model may produce evidence, but only these rules change the
map (domain-model.md, Agents).

    unexplored --evidence--> attempted --more, scoring ok--> practiced
    practiced --three good ones--> solid --no practice for decay_days--> rusty
    rusty --evidence--> practiced
"""

from datetime import datetime, timedelta

from app.domain.entities import Analysis, SkillState, SkillStatus

#: Evidence below this confidence does not count as an attempt.
MIN_CONFIDENCE = 0.6
#: How many recent shot ids a skill remembers.
SHOT_MEMORY = 10
PRACTICED_MIN_ATTEMPTS = 2
PRACTICED_MIN_SCORE = 5
SOLID_MIN_ATTEMPTS = 3
SOLID_MIN_BEST = 7
SOLID_MIN_LAST = 6


def apply_analysis(
    skills: dict[str, SkillState],
    analysis: Analysis,
    at: datetime,
    min_confidence: float = MIN_CONFIDENCE,
) -> list[SkillState]:
    """Return the skills this analysis changed, already updated.

    ``skills`` is the user's current map keyed by technique id; techniques
    missing from it are unexplored. Applying the same analysis twice is a
    no-op because the shot id is remembered.
    """
    changed: list[SkillState] = []
    for evidence in analysis.techniques:
        if evidence.confidence < min_confidence:
            continue
        state = skills.get(evidence.technique_id) or SkillState(
            user_id=analysis.user_id, technique_id=evidence.technique_id
        )
        if analysis.shot_id in state.shot_ids:
            continue
        state.attempts += 1
        state.last_score = analysis.score
        state.best_score = max(state.best_score, analysis.score)
        state.last_practiced = at
        state.shot_ids = [*state.shot_ids, analysis.shot_id][-SHOT_MEMORY:]
        state.status = _status_after_attempt(state)
        skills[evidence.technique_id] = state
        changed.append(state)
    return changed


def _status_after_attempt(state: SkillState) -> SkillStatus:
    if (
        state.attempts >= SOLID_MIN_ATTEMPTS
        and state.best_score >= SOLID_MIN_BEST
        and state.last_score >= SOLID_MIN_LAST
    ):
        return SkillStatus.SOLID
    if state.attempts >= PRACTICED_MIN_ATTEMPTS and state.last_score >= PRACTICED_MIN_SCORE:
        return SkillStatus.PRACTICED
    return SkillStatus.ATTEMPTED


def decay(skills: dict[str, SkillState], now: datetime, decay_days: int) -> list[SkillState]:
    """Solid skills not practised for ``decay_days`` become rusty. Returns the changed ones."""
    changed: list[SkillState] = []
    cutoff = now - timedelta(days=decay_days)
    for state in skills.values():
        if (
            state.status is SkillStatus.SOLID
            and state.last_practiced is not None
            and state.last_practiced < cutoff
        ):
            state.status = SkillStatus.RUSTY
            changed.append(state)
    return changed


def attempted_ids(skills: dict[str, SkillState]) -> set[str]:
    """Techniques that count as at least attempted, for prerequisite checks."""
    return {tid for tid, s in skills.items() if s.status is not SkillStatus.UNEXPLORED}
