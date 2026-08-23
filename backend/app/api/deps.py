"""Process-wide wiring: which real implementation of each port this process uses.

Picked from settings once, at import. Local by default; any cloud setting
switches that one port to its cloud implementation. Tests build their own
``Context`` and never touch this module.
"""

from fastapi import Depends, Request

from app.api.auth import current_user
from app.config import settings
from app.infra.bus import TOPICS, InProcessBus, PubSubBus
from app.infra.drive import GoogleDriveClient, LocalDriveClient
from app.infra.secrets import LocalTokenStore, SecretManagerTokenStore
from app.infra.storage import GcsBlobStore, LocalBlobStore
from app.infra.store import FileStore, FirestoreStore
from app.services.context import Context


def build_context() -> Context:
    store = (
        FirestoreStore() if settings.cloud_state else FileStore(settings.blob_root + "/store.json")
    )
    blobs = GcsBlobStore() if settings.gcs_bucket else LocalBlobStore()
    tokens = SecretManagerTokenStore() if settings.cloud_state else LocalTokenStore()
    bus = InProcessBus() if settings.in_process_pipeline else PubSubBus()
    drive = (
        LocalDriveClient(settings.drive_local_folder)
        if settings.drive_local_folder
        else GoogleDriveClient()
    )
    return Context(store=store, blobs=blobs, bus=bus, drive=drive, tokens=tokens)


def wire(ctx: Context) -> None:
    """Register every stage handler. Same registrations on either bus."""
    from app.infra import repository
    from app.services import analyst, cartographer, director, ingest, judge, scout, scribe

    async def on_media_new(message: dict) -> None:
        await ingest.ingest(ctx, message)

    async def on_media_ingested(message: dict) -> None:
        await analyst.analyse(ctx, message)

    async def on_media_analyzed(message: dict) -> None:
        await cartographer.update(ctx, message)
        # The map moved; if this user has never had a quest, that is enough to
        # choose one. Nothing to click, on the first run or any other.
        shot = await repository.get_shot(ctx.store, message["shot_id"])
        await scout.issue_first(ctx, shot.user_id)

    async def on_media_analyzed_judge(message: dict) -> None:
        await judge.judge(ctx, message)

    async def on_quest_closed(message: dict) -> None:
        await scout.on_quest_closed(ctx, message)

    async def on_quest_issued(message: dict) -> None:
        await director.direct(ctx, message)

    async def on_media_judged(message: dict) -> None:
        await scribe.write_review(ctx, message)

    # Stage names match the push subscriptions in infra/topics.sh.
    ctx.bus.subscribe(TOPICS["media.new"], on_media_new, stage="ingest")
    ctx.bus.subscribe(TOPICS["media.ingested"], on_media_ingested, stage="analyst")
    ctx.bus.subscribe(TOPICS["media.analyzed"], on_media_analyzed, stage="cartographer")
    ctx.bus.subscribe(TOPICS["media.analyzed"], on_media_analyzed_judge, stage="judge")
    ctx.bus.subscribe(TOPICS["media.judged"], on_media_judged, stage="scribe")
    ctx.bus.subscribe(TOPICS["quest.closed"], on_quest_closed, stage="scout")
    ctx.bus.subscribe(TOPICS["quest.issued"], on_quest_issued, stage="director")


context = build_context()
wire(context)


def get_context() -> Context:
    return context


async def signed_in(request: Request, user: dict = Depends(current_user)) -> dict:
    return user


def describe() -> dict:
    """For /api/health: which implementation each port resolved to."""
    return {
        "store": type(context.store).__name__,
        "blobs": type(context.blobs).__name__,
        "tokens": type(context.tokens).__name__,
        "bus": type(context.bus).__name__,
        "drive": type(context.drive).__name__,
    }
