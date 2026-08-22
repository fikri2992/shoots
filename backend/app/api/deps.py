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
    from app.services import analyst, ingest

    async def on_media_new(message: dict) -> None:
        await ingest.ingest(ctx, message)

    async def on_media_ingested(message: dict) -> None:
        await analyst.analyse(ctx, message)

    ctx.bus.subscribe(TOPICS["media.new"], on_media_new)
    ctx.bus.subscribe(TOPICS["media.ingested"], on_media_ingested)


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
