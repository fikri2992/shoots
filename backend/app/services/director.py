"""Director stage: ``quest.issued`` → reference clip on the quest.

The Scout says what to shoot; the Director shows it. A Veo clip of the
technique lands on ``quest.reference_clip`` as a blob the quest card plays
inline. Idempotent on the quest: a second delivery finds the blob and stops.
The clip is a nicety, so if the quest was closed meanwhile nothing is
generated, and a Veo failure raises: Pub/Sub retries, then dead-letters, and
the quest simply has no clip.
"""

import logging

from app.agents import director as agent
from app.config import settings
from app.domain import taxonomy
from app.domain.entities import QuestStatus
from app.infra import repository as repo
from app.infra.storage import quest_blob_path
from app.services.context import Context

logger = logging.getLogger(__name__)

AGENT = "director"


async def direct(
    ctx: Context, message: dict, generators: agent.Generators | None = None
) -> str | None:
    """Returns the blob path of the clip, or None when there was nothing to do."""
    quest = await repo.get_quest(ctx.store, message["quest_id"])
    if quest.reference_clip and await ctx.blobs.exists(quest.reference_clip):
        logger.info("director: %s already has a clip", quest.id)
        return quest.reference_clip
    if quest.status is not QuestStatus.OPEN:
        logger.info("director: %s is %s, no clip", quest.id, quest.status.value)
        return None

    gen = generators or agent.vertex_generators()
    technique = taxonomy.get(quest.technique_id)

    board = await gen.storyboard(technique, quest)
    await repo.record(
        ctx.store,
        quest.user_id,
        AGENT,
        "storyboard",
        {"video_prompt": board.video_prompt},
        quest_id=quest.id,
    )

    clip = await gen.clip(board.video_prompt)
    path = quest_blob_path(quest.user_id, quest.id, "reference", "mp4")
    await ctx.blobs.write(path, clip, "video/mp4")

    # Re-read: the Judge may have closed the quest while Veo was rendering.
    quest = await repo.get_quest(ctx.store, quest.id)
    quest.reference_clip = path
    await repo.put_quest(ctx.store, quest)
    await repo.record(
        ctx.store,
        quest.user_id,
        AGENT,
        "clip_ready",
        {"seconds": settings.clip_seconds, "bytes": len(clip), "video_model": settings.model_video},
        quest_id=quest.id,
    )
    return path
