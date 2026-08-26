"""Optional legacy Director: manually generate a reference clip.

A manually requested Veo clip may land on ``experiment.reference_clip``. No
topic, subscription, Scout call, or core UI depends on it. The conditional
write cannot revive a closed Experiment; an orphaned blob is deleted.
"""

import logging

from app.agents import director as agent
from app.config import settings
from app.domain import taxonomy
from app.domain.entities import ExperimentStatus
from app.infra import repository as repo
from app.infra.storage import experiment_blob_path
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "director"


async def direct(
    ctx: Context, message: dict, generators: agent.Generators | None = None
) -> str | None:
    """Returns the blob path of the clip, or None when there was nothing to do."""
    experiment = await repo.get_experiment(ctx.store, message["experiment_id"])
    if experiment.reference_clip and await ctx.blobs.exists(experiment.reference_clip):
        logger.info("director: %s already has a clip", experiment.id)
        return experiment.reference_clip
    if experiment.status is not ExperimentStatus.OPEN:
        logger.info("director: %s is %s, no clip", experiment.id, experiment.status.value)
        return None

    gen = generators or agent.vertex_generators()
    technique = taxonomy.get(experiment.technique_id)

    board = await gen.storyboard(technique, experiment)
    await repo.record(
        ctx.store,
        experiment.user_id,
        AGENT,
        "storyboard",
        {"video_prompt": board.video_prompt},
        experiment_id=experiment.id,
    )

    clip = await gen.clip(board.video_prompt)
    path = experiment_blob_path(experiment.user_id, experiment.id, "reference", "mp4")
    await ctx.blobs.write(path, clip, "video/mp4")

    # Atomic status gate: closing can race this exact write without being
    # overwritten or resurrected by the stale Experiment object above.
    if not await repo.attach_reference_clip_if_open(ctx.store, experiment.id, path):
        await ctx.blobs.delete(path)
        logger.info("director: %s closed while rendering; discarded clip", experiment.id)
        return None
    await repo.record(
        ctx.store,
        experiment.user_id,
        AGENT,
        "clip_ready",
        {"seconds": settings.clip_seconds, "bytes": len(clip), "video_model": settings.model_video},
        experiment_id=experiment.id,
    )
    return path
