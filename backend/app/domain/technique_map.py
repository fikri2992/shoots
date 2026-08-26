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
would benefit from revisiting something is a *selection* question that still
needs a supported Experiment Direction, not a state or timer that expires.

Promotion reads the Technique's own Evidence. Overall and element scores are
not stored (decision 61), because one opinion about a whole Shot cannot
measure every Technique visible inside it.

What *is* about one Technique is how the panel saw it: how many lenses agreed
and how sure they were. The map tracks recurrence and makes no quality claim.
"""

from datetime import datetime

from app.domain.entities import Analysis, TechniqueEvidence, TechniqueState, TechniqueStatus

#: Evidence below this confidence does not count as an observation.
MIN_CONFIDENCE = 0.6
#: How many recent Shot ids a Technique state remembers.
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
    states: dict[str, TechniqueState],
    analysis: Analysis,
    at: datetime,
    min_confidence: float = MIN_CONFIDENCE,
) -> list[TechniqueState]:
    """Return the Technique states this Analysis changed, already updated.

    ``states`` is the user's current map keyed by Technique id; Techniques
    missing from it are unobserved. Applying the same analysis twice is a
    no-op because the shot id is remembered.
    """
    changed: list[TechniqueState] = []
    for evidence in analysis.techniques:
        if evidence.confidence < min_confidence:
            continue
        state = states.get(evidence.technique_id) or TechniqueState(
            user_id=analysis.user_id, technique_id=evidence.technique_id
        )
        if analysis.shot_id in state.shot_ids:
            continue
        state.attempts += 1
        state.corroborated += corroborated(evidence)
        state.best_confidence = max(state.best_confidence, evidence.confidence)
        state.last_observed = at
        state.shot_ids = [*state.shot_ids, analysis.shot_id][-SHOT_MEMORY:]
        state.status = _status_after_attempt(state)
        states[evidence.technique_id] = state
        changed.append(state)
    return changed


def _status_after_attempt(state: TechniqueState) -> TechniqueStatus:
    if state.attempts <= 0:
        return TechniqueStatus.UNOBSERVED
    if (
        state.attempts >= RECURRING_MIN_ATTEMPTS
        and state.corroborated >= RECURRING_MIN_CORROBORATED
    ):
        return TechniqueStatus.RECURRING
    return TechniqueStatus.OBSERVED


def normalise_state(state: TechniqueState) -> TechniqueState:
    """Return a state whose label is supported by its own Evidence counts.

    Old graded records could migrate a `solid` label while carrying no
    corroboration count. The counts are the authority now: persistence may be
    legacy, but no service or surface may repeat an impossible recurrence.
    """
    expected = _status_after_attempt(state)
    return state if state.status is expected else state.model_copy(update={"status": expected})


def observed_ids(states: dict[str, TechniqueState]) -> set[str]:
    """Techniques the Evidence has seen at least once."""
    return {tid for tid, state in states.items() if state.status is not TechniqueStatus.UNOBSERVED}
