"""Explicit replacement of one retired aperture-proxy Experiment, not general creation."""

from app.domain.entities import Experiment, ExperimentStatus, ExperimentType
from app.infra import repository as repo
from app.services import interventions, scout
from app.services.context import Context


async def correct(ctx: Context, user_id: str, previous_id: str) -> Experiment:
    previous = await repo.find_experiment(ctx.store, previous_id)
    if previous is None or previous.user_id != user_id:
        raise repo.UnknownEntity(f"experiment {previous_id}")
    if not previous.criteria_notice:
        raise ValueError("This Experiment does not need a Criteria correction")
    replacement_id = repo.corrected_experiment_id(user_id, previous_id)
    replacement = await repo.find_experiment(ctx.store, replacement_id)
    if replacement is not None:
        if (
            replacement.user_id != user_id
            or replacement.type is not ExperimentType.REPRODUCE
            or replacement.technique_id != previous.technique_id
            or replacement.criteria_notice
        ):
            raise ValueError("The stored replacement does not match this correction")
        await interventions.refresh_for_experiment(ctx, previous_id)
        return replacement
    opened = await repo.open_experiment(ctx.store, user_id)
    if previous.status is not ExperimentStatus.OPEN or opened is None or opened.id != previous_id:
        raise ValueError("The old Experiment is no longer the open focus; nothing was replaced")
    replacement = await scout.issue(
        ctx,
        user_id,
        force=True,
        technique_id=previous.technique_id,
        requested_reason="criteria_correction",
        experiment_id=replacement_id,
        replaces_legacy_id=previous_id,
    )
    if replacement is None:
        raise ValueError("No current Keeper supports this Experiment. Your old record is unchanged")
    await interventions.refresh_for_experiment(ctx, previous_id)
    return replacement
