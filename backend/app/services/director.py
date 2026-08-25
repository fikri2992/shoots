"""Director stage: ``experiment.issued`` → reference clip on the experiment.

The Scout says what to shoot; the Director shows it. A Veo clip of the
technique lands on ``experiment.reference_clip`` as a blob the experiment card plays
inline. Idempotent on the experiment: a second delivery finds the blob and stops.
The clip is a nicety, so if the experiment was closed meanwhile nothing is
generated, and a Veo failure raises: Pub/Sub retries, then dead-letters, and
the experiment simply has no clip.
"""

import logging

from app.agents import director as agent
from app.config import settings
from app.domain import taxonomy
from app.domain.entities import ExperimentStatus
from app.infra import repository as repo
from app.infra.storage import quest_blob_path
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
    path = quest_blob_path(experiment.user_id, experiment.id, "reference", "mp4")
    await ctx.blobs.write(path, clip, "video/mp4")

    # Re-read: the Judge may have closed the experiment while Veo was rendering.
    experiment = await repo.get_experiment(ctx.store, experiment.id)
    experiment.reference_clip = path
    await repo.put_experiment(ctx.store, experiment)
    await repo.record(
        ctx.store,
        experiment.user_id,
        AGENT,
        "clip_ready",
        {"seconds": settings.clip_seconds, "bytes": len(clip), "video_model": settings.model_video},
        experiment_id=experiment.id,
    )
    return path
