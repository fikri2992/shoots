"""Pure Run transitions.

Events explain a pipeline. A Run settles it. Independent Pub/Sub stages may
finish in any order, so no individual handler gets to declare completion.
"""

from datetime import datetime
from typing import Any

from app.domain.entities import (
    Run,
    RunStage,
    RunStatus,
    RunStep,
    RunStepState,
    Shot,
    now,
)

SETTLED = {RunStepState.COMPLETED, RunStepState.SKIPPED, RunStepState.TERMINAL}


def for_shot(shot: Shot) -> Run:
    return Run(
        id=f"run_{shot.id}",
        user_id=shot.user_id,
        shot_id=shot.id,
        source=shot.source,
        experiment_id=shot.experiment_id,
        started_at=shot.ingested_at,
    )


def advance(
    current: Run,
    stage: RunStage,
    state: RunStepState,
    outcome: str,
    detail: dict[str, Any] | None = None,
    at: datetime | None = None,
) -> Run:
    """Return the next Run without mutating the stored instance."""
    if current.status in {RunStatus.COMPLETED, RunStatus.TERMINAL}:
        return current

    changed_at = at or now()
    updated = current.model_copy(deep=True)
    previous = updated.steps.get(stage.value, RunStep())
    if previous.state in SETTLED:
        return current

    updated.steps[stage.value] = RunStep(
        state=state,
        outcome=outcome,
        detail=detail or {},
        settled_at=changed_at if state in SETTLED else None,
    )
    updated.updated_at = changed_at

    if state is RunStepState.TERMINAL:
        for pending_stage, step in updated.steps.items():
            if step.state not in SETTLED:
                updated.steps[pending_stage] = RunStep(
                    state=RunStepState.SKIPPED,
                    outcome="Run stopped before this stage",
                    settled_at=changed_at,
                )
        updated.status = RunStatus.TERMINAL
        updated.completed_at = changed_at
        return updated

    states = [step.state for step in updated.steps.values()]
    if all(step in SETTLED for step in states):
        updated.status = RunStatus.COMPLETED
        updated.completed_at = changed_at
    elif RunStepState.RETRYING in states:
        updated.status = RunStatus.RETRYING
        updated.completed_at = None
    else:
        updated.status = RunStatus.RUNNING
        updated.completed_at = None
    return updated
