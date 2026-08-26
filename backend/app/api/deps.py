"""Process-wide wiring: which real implementation of each port this process uses.

Picked from settings once, at import. Local by default; any cloud setting
switches that one port to its cloud implementation. Tests build their own
``Context`` and never touch this module.
"""

from app.config import settings
from app.infra.bus import TOPICS, InProcessBus, PubSubBus
from app.infra.drive import GoogleDriveClient, LocalDriveClient
from app.infra.mobile_push import FirebaseMobilePush
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
    mobile_push = (
        FirebaseMobilePush(settings.gcp_project)
        if settings.cloud_state and settings.gcp_project
        else None
    )
    return Context(
        store=store,
        blobs=blobs,
        bus=bus,
        drive=drive,
        tokens=tokens,
        mobile_push=mobile_push,
    )


def wire(ctx: Context) -> None:
    """Register every stage handler. Same registrations on either bus."""
    from app.domain.entities import ExperimentType, RunStage, ShotStatus
    from app.infra import repository
    from app.services import analyst, cartographer, ingest, judge, runs, scout, scribe

    async def on_media_new(message: dict) -> None:
        try:
            await ingest.ingest(ctx, message)
        except Exception as error:
            await runs.retrying(
                ctx,
                message["shot_id"],
                RunStage.INGEST,
                "Ingest will retry",
                {"error": f"{type(error).__name__}: {error}"[:500]},
            )
            raise
        shot = await repository.get_shot(ctx.store, message["shot_id"])
        if shot.status is ShotStatus.FAILED:
            await runs.terminal(
                ctx,
                shot.id,
                RunStage.INGEST,
                "Ingest proved the Shot unreadable",
                {"error": shot.error},
            )
        elif shot.status in {
            ShotStatus.INGESTED,
            ShotStatus.ANALYSING,
            ShotStatus.ANALYZED,
        }:
            await runs.completed(ctx, shot.id, RunStage.INGEST, "Media measured and prepared")

    async def on_media_ingested(message: dict) -> None:
        try:
            await analyst.analyse(ctx, message)
        except Exception as error:
            await runs.retrying(
                ctx,
                message["shot_id"],
                RunStage.ANALYST,
                "Analyst will retry",
                {"error": f"{type(error).__name__}: {error}"[:500]},
            )
            raise
        shot = await repository.get_shot(ctx.store, message["shot_id"])
        if shot.status is ShotStatus.ANALYZED:
            await runs.completed(ctx, shot.id, RunStage.ANALYST, "Visual reading stored")

    async def on_media_analyzed(message: dict) -> None:
        try:
            await cartographer.update(ctx, message)
            await runs.completed(
                ctx,
                message["shot_id"],
                RunStage.CARTOGRAPHER,
                "Technique Map and longitudinal record checked",
            )
        except Exception as error:
            await runs.retrying(
                ctx,
                message["shot_id"],
                RunStage.CARTOGRAPHER,
                "Cartographer will retry",
                {"error": f"{type(error).__name__}: {error}"[:500]},
            )
            raise

        shot = await repository.get_shot(ctx.store, message["shot_id"])
        experiment = (
            await repository.find_experiment(ctx.store, shot.experiment_id)
            if shot.experiment_id
            else None
        )
        if experiment is not None and experiment.type is ExperimentType.REPRODUCE:
            return
        try:
            outcome = await scout.consider_after_shot(ctx, shot.user_id, shot.id)
            await runs.completed(ctx, shot.id, RunStage.SCOUT, outcome)
        except Exception as error:
            await runs.retrying(
                ctx,
                shot.id,
                RunStage.SCOUT,
                "Scout will retry",
                {"error": f"{type(error).__name__}: {error}"[:500]},
            )
            raise

    async def on_media_analyzed_judge(message: dict) -> None:
        try:
            outcome = await judge.judge(ctx, message)
            if outcome in {
                "free Shot; no Experiment judgment",
                "Shot is not an explicit Reproduce result",
            } or outcome.endswith("creates no Verdict"):
                await runs.skipped(ctx, message["shot_id"], RunStage.JUDGE, outcome)
            else:
                await runs.completed(ctx, message["shot_id"], RunStage.JUDGE, outcome)
        except Exception as error:
            await runs.retrying(
                ctx,
                message["shot_id"],
                RunStage.JUDGE,
                "Judge will retry",
                {"error": f"{type(error).__name__}: {error}"[:500]},
            )
            raise

        shot = await repository.get_shot(ctx.store, message["shot_id"])
        if shot.capture_session_id:
            await runs.skipped(
                ctx,
                shot.id,
                RunStage.SCOUT,
                "Capture Session owns the batch Experiment transition",
            )
        elif shot.experiment_id and outcome != "Reproduce Criteria met":
            await runs.skipped(
                ctx,
                shot.id,
                RunStage.SCOUT,
                "The associated Experiment remained open or had already settled",
            )

    async def on_experiment_closed(message: dict) -> None:
        outcome = await scout.on_experiment_closed(ctx, message)
        if message.get("shot_id"):
            await runs.completed(ctx, message["shot_id"], RunStage.SCOUT, outcome)

    async def on_keeper_changed(message: dict) -> None:
        if message.get("keeper"):
            await scout.issue(ctx, message["user_id"])

    async def on_account_delete(message: dict) -> None:
        from app.services import account

        await account.delete(ctx, message["user_id"])

    async def on_media_judged(message: dict) -> None:
        try:
            output_id = await scribe.write_review(ctx, message)
            await runs.completed(
                ctx,
                message["shot_id"],
                RunStage.SCRIBE,
                "Reviewed Shot written to Drive" if output_id else "External write not available",
                {"external_write": bool(output_id)},
            )
        except Exception as error:
            await runs.retrying(
                ctx,
                message["shot_id"],
                RunStage.SCRIBE,
                "Scribe will retry",
                {"error": f"{type(error).__name__}: {error}"[:500]},
            )
            raise

    # Stage names match the push subscriptions in infra/topics.sh.
    ctx.bus.subscribe(TOPICS["media.new"], on_media_new, stage="ingest")
    ctx.bus.subscribe(TOPICS["media.ingested"], on_media_ingested, stage="analyst")
    ctx.bus.subscribe(TOPICS["media.analyzed"], on_media_analyzed, stage="cartographer")
    ctx.bus.subscribe(TOPICS["media.analyzed"], on_media_analyzed_judge, stage="judge")
    ctx.bus.subscribe(TOPICS["media.judged"], on_media_judged, stage="scribe")
    ctx.bus.subscribe(TOPICS["experiment.closed"], on_experiment_closed, stage="scout")
    ctx.bus.subscribe(TOPICS["keeper.changed"], on_keeper_changed, stage="scout-signal")
    ctx.bus.subscribe(TOPICS["account.delete"], on_account_delete, stage="account-delete")


context = build_context()
wire(context)


def get_context() -> Context:
    return context


def describe() -> dict:
    """For /api/health: which implementation each port resolved to."""
    return {
        "store": type(context.store).__name__,
        "blobs": type(context.blobs).__name__,
        "tokens": type(context.tokens).__name__,
        "bus": type(context.bus).__name__,
        "drive": type(context.drive).__name__,
    }
