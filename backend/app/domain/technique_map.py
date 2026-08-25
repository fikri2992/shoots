"""The Technique Map: how Evidence moves a Technique through the record.

Pure functions over ``TechniqueState``. Reproducible from stored analyses,
which is the point: a model may produce Evidence, but only these rules change
the record (domain-model.md, decision 46).

    unobserved --evidence--> observed --corroborated three times--> recurring

Three states, and every one of them is a statement about the Evidence rather
than about the photographer. There is no `solid`, because that grades a
person; no `practiced`, because two sightings and three are the same claim
with a different adjective; and no decay, because a Technique that recurred
did recur, and a month of rain does not make that untrue. A photographer who
would benefit from revisiting something is a *selection* question, answered by
the Scout's ranking from ``last_observed``, not by a state that expires.

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

from app.domain.entities import Analysis, TechniqueEvidence, TechniqueState, TechniqueStatus

#: Evidence below this confidence does not count as an observation.
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

#: What "recurring" costs. Three separate corroborated sightings - the same bar
#: the old `solid` used, kept because it is the one the corpus was measured
#: against: it dropped 16 techniques to 6, and the ten that fell were the ones
#: no second lens ever saw (docs/research-findings.md).
RECURRING_MIN_ATTEMPTS = 3
RECURRING_MIN_CORROBORATED = 3


def corroborated(evidence: TechniqueEvidence) -> bool:
    """Did more than one lens see this, and mean it?"""
    return (
        evidence.agreement >= CORROBORATED_AGREEMENT
        and evidence.confidence >= CORROBORATED_CONFIDENCE
    )


def apply_analysis(
    skills: dict[str, TechniqueState],
    analysis: Analysis,
    at: datetime,
    min_confidence: float = MIN_CONFIDENCE,
) -> list[TechniqueState]:
    """Return the skills this analysis changed, already updated.

    ``skills`` is the user's current map keyed by technique id; techniques
    missing from it are unobserved. Applying the same analysis twice is a
    no-op because the shot id is remembered.
    """
    changed: list[TechniqueState] = []
    for evidence in analysis.techniques:
        if evidence.confidence < min_confidence:
            continue
        state = skills.get(evidence.technique_id) or TechniqueState(
            user_id=analysis.user_id, technique_id=evidence.technique_id
        )
        if analysis.shot_id in state.shot_ids:
            continue
        state.attempts += 1
        state.corroborated += corroborated(evidence)
        state.best_confidence = max(state.best_confidence, evidence.confidence)
        state.last_score = analysis.score
        state.best_score = max(state.best_score, analysis.score)
        state.last_observed = at
        state.shot_ids = [*state.shot_ids, analysis.shot_id][-SHOT_MEMORY:]
        state.status = _status_after_attempt(state)
        skills[evidence.technique_id] = state
        changed.append(state)
    return changed


def _status_after_attempt(state: TechniqueState) -> TechniqueStatus:
    if (
        state.attempts >= RECURRING_MIN_ATTEMPTS
        and state.corroborated >= RECURRING_MIN_CORROBORATED
    ):
        return TechniqueStatus.RECURRING
    return TechniqueStatus.OBSERVED


def stale_ids(
    skills: dict[str, TechniqueState], now: datetime, after_days: int
) -> set[str]:
    """Techniques not seen for a while. Worth offering again, not a state.

    The record used to expire ``solid`` into ``rusty`` here, which said the
    photographer had got worse at something while all that had actually
    happened was time. What recurred still recurred; whether it is interesting
    to revisit is the Scout's question, and this answers it without touching
    what the record claims.
    """
    changed: set[str] = set()
    cutoff = now - timedelta(days=after_days)
    for tid, state in skills.items():
        last = state.last_observed
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=cutoff.tzinfo)  # older records from zone-less EXIF
        if state.status is TechniqueStatus.RECURRING and last is not None and last < cutoff:
            changed.add(tid)
    return changed


def observed_ids(skills: dict[str, TechniqueState]) -> set[str]:
    """Techniques the Evidence has seen at least once, for prerequisite checks."""
    return {tid for tid, s in skills.items() if s.status is not TechniqueStatus.UNOBSERVED}
