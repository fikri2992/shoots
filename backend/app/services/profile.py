"""Build the photographer's Tendency Profile from the complete archive."""

from app.domain import tendency
from app.domain.entities import ModelProvenance, Provenance
from app.infra import repository as repo
from app.services.context import Context


async def build(ctx: Context, user_id: str) -> tendency.Profile:
    """One bulk Shot read and one bulk Analysis read; no sliding corpus cap."""
    shots = await repo.list_shots(ctx.store, user_id)
    analyses = {
        analysis.shot_id: analysis for analysis in await repo.list_analyses(ctx.store, user_id)
    }
    # A queued, retrying, or terminally unreadable file is not yet a decision
    # point in the photographer's record. Every Shot the Analyst actually read
    # remains included, with no recency cap.
    rows = [(shot, analyses[shot.id]) for shot in shots if shot.id in analyses]
    keepers = {shot.id for shot, _ in rows if shot.kept_at}
    return tendency.build(rows, keepers)


async def build_for_shots(ctx: Context, user_id: str, shot_ids: set[str]) -> tendency.Profile:
    """Build the same Profile over an explicit, frozen Shot set.

    Reproduce Change uses this boundary so unrelated free Shots cannot be
    mistaken for behavior inside an Experiment.
    """
    shots = [shot for shot in await repo.list_shots(ctx.store, user_id) if shot.id in shot_ids]
    analyses = {
        analysis.shot_id: analysis
        for analysis in await repo.list_analyses(ctx.store, user_id)
        if analysis.shot_id in shot_ids
    }
    rows = [(shot, analyses[shot.id]) for shot in shots if shot.id in analyses]
    keepers = {shot.id for shot, _ in rows if shot.kept_at}
    return tendency.build(rows, keepers)


def provenance(profile: tendency.Profile) -> Provenance:
    """Provenance shared by Baselines and Journey Updates."""
    return Provenance(
        shot_ids=list(profile.shot_ids),
        sample_size=profile.shots,
        calc_version=profile.calc_version,
        inputs=[
            ModelProvenance(model=model, prompt_version=prompt_version)
            for model, prompt_version in profile.model_inputs
        ],
        analysis_versions=dict(profile.analysis_versions),
    )
