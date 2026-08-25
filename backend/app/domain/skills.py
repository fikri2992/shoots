"""The Cartographer's rules: how evidence moves a technique through the graph.

Pure functions over ``SkillState``. Reproducible from stored analyses, which
is the point: a model may produce evidence, but only these rules change the
map (domain-model.md, Agents).

    unexplored --evidence--> attempted --seen again, corroborated once--> practiced
    practiced --three corroborated--> solid --no practice for decay_days--> rusty
    rusty --evidence--> practiced

Promotion reads the technique's own evidence and never the frame's score.
``Analysis.score`` is one number for the whole photograph, so a frame
demonstrating six techniques used to hand all six whatever the frame earned:
measured over the corpus that put 32 of 37 skills at a best score of 8 or 9
from 18 shots, and 16 of them at solid. The rubric will not separate them
either — its five elements correlate at r = 0.89 and the weighted mean tracks
``impact`` alone at 0.986 (docs/research-findings.md, §1 and §5).

What *is* about one technique is how the panel saw it: how many lenses agreed
and how sure they were. So the map tracks reliability, which is what a skill
graph is for, and makes no claim about quality, which it cannot measure.
"""

from datetime import datetime, timedelta

from app.domain.entities import Analysis, SkillState, SkillStatus, TechniqueEvidence

#: Evidence below this confidence does not count as an attempt.
MIN_CONFIDENCE = 0.6
#: How many recent shot ids a skill remembers.
SHOT_MEMORY = 10

#: What corroboration means. The panel lets evidence through on two lenses *or*
#: the owning lens alone at 0.75 (domain/panel.py); this asks for both, because
#: one lens repeating itself across three frames is one opinion three times.
#: The lenses differ in instruction and input by design, so two of them agreeing
#: is the only independence the system actually has.
CORROBORATED_AGREEMENT = 2
CORROBORATED_CONFIDENCE = 0.75

PRACTICED_MIN_ATTEMPTS = 2
PRACTICED_MIN_CORROBORATED = 1
SOLID_MIN_ATTEMPTS = 3
SOLID_MIN_CORROBORATED = 3


def corroborated(evidence: TechniqueEvidence) -> bool:
    """Did more than one lens see this, and mean it?"""
    return (
        evidence.agreement >= CORROBORATED_AGREEMENT
        and evidence.confidence >= CORROBORATED_CONFIDENCE
    )


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
        state.corroborated += corroborated(evidence)
        state.best_confidence = max(state.best_confidence, evidence.confidence)
        state.last_score = analysis.score
        state.best_score = max(state.best_score, analysis.score)
        state.last_practiced = at
        state.shot_ids = [*state.shot_ids, analysis.shot_id][-SHOT_MEMORY:]
        state.status = _status_after_attempt(state)
        skills[evidence.technique_id] = state
        changed.append(state)
    return changed


def _status_after_attempt(state: SkillState) -> SkillStatus:
    if state.attempts >= SOLID_MIN_ATTEMPTS and state.corroborated >= SOLID_MIN_CORROBORATED:
        return SkillStatus.SOLID
    if (
        state.attempts >= PRACTICED_MIN_ATTEMPTS
        and state.corroborated >= PRACTICED_MIN_CORROBORATED
    ):
        return SkillStatus.PRACTICED
    return SkillStatus.ATTEMPTED


def decay(skills: dict[str, SkillState], now: datetime, decay_days: int) -> list[SkillState]:
    """Solid skills not practised for ``decay_days`` become rusty. Returns the changed ones."""
    changed: list[SkillState] = []
    cutoff = now - timedelta(days=decay_days)
    for state in skills.values():
        last = state.last_practiced
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=cutoff.tzinfo)  # older records from zone-less EXIF
        if state.status is SkillStatus.SOLID and last is not None and last < cutoff:
            state.status = SkillStatus.RUSTY
            changed.append(state)
    return changed


def attempted_ids(skills: dict[str, SkillState]) -> set[str]:
    """Techniques that count as at least attempted, for prerequisite checks."""
    return {tid for tid, s in skills.items() if s.status is not SkillStatus.UNEXPLORED}
