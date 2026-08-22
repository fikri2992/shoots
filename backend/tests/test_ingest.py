"""Ingest end to end on real files with real stores: a directory as the Drive
folder, the in-memory store, blobs on disk, the in-process bus."""

import pytest
from PIL import Image

from app.config import settings
from app.domain.entities import ShotKind, ShotStatus, User
from app.infra import repository as repo
from app.infra.bus import TOPICS, InProcessBus
from app.infra.drive import LocalDriveClient
from app.infra.secrets import LocalTokenStore
from app.infra.storage import GRIDDED, ORIGINAL, SHEET, THUMB, LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import ingest
from app.services.context import Context
from tests.fixtures import HAS_FFMPEG, jpeg_with_exif, two_shot_video

USER = User(id="u_test", email="t@example.com", drive_folder_id="local")


def make_context(tmp_path) -> Context:
    folder = tmp_path / "drive"
    folder.mkdir()
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=LocalDriveClient(folder),
        tokens=LocalTokenStore(tmp_path / "tokens"),
    )

    async def on_new(message):
        await ingest.ingest(ctx, message)

    ctx.bus.subscribe(TOPICS["media.new"], on_new)
    return ctx


async def test_photo_flows_from_folder_to_ingested(tmp_path):
    ctx = make_context(tmp_path)
    (tmp_path / "drive" / "IMG_001.jpg").write_bytes(jpeg_with_exif(width=1600, height=900))
    (tmp_path / "drive" / "notes.txt").write_text("not media")
    await repo.put_user(ctx.store, USER)

    created = await ingest.sync(ctx, USER)
    assert len(created) == 1 and created[0].status is ShotStatus.NEW
    await ctx.bus.drain()

    shot = await repo.get_shot(ctx.store, created[0].id)
    assert shot.status is ShotStatus.INGESTED
    assert shot.kind is ShotKind.PHOTO
    assert shot.exif.f_number == 5.6 and shot.exif.exposure_time_s == 1 / 30
    assert shot.captured_at is not None
    assert set(shot.blobs) == {ORIGINAL, GRIDDED, THUMB}

    # The gridded frame is what the Analyst sees: within the cap, grid matches.
    gridded = Image.open(tmp_path / "blobs" / shot.blobs[GRIDDED])
    assert max(gridded.size) <= settings.analyst_max_edge
    assert (shot.grid.width, shot.grid.height) == gridded.size
    assert shot.grid.cols * shot.grid.rows >= 48  # near the 64-cell target for 16:9

    stages = [e.stage for e in await repo.list_events(ctx.store, USER.id)]
    assert "ingested" in stages and "queued" in stages


async def test_sync_is_idempotent_and_redelivery_is_a_noop(tmp_path):
    ctx = make_context(tmp_path)
    (tmp_path / "drive" / "a.jpg").write_bytes(jpeg_with_exif())
    await repo.put_user(ctx.store, USER)

    first = await ingest.sync(ctx, USER)
    second = await ingest.sync(ctx, USER)
    assert len(first) == 1 and second == []
    await ctx.bus.drain()

    shot = await repo.get_shot(ctx.store, first[0].id)
    before = shot.model_dump()
    await ingest.ingest(ctx, {"shot_id": shot.id})  # Pub/Sub redelivery
    after = (await repo.get_shot(ctx.store, shot.id)).model_dump()
    assert before == after


async def test_renamed_file_is_the_same_shot(tmp_path):
    ctx = make_context(tmp_path)
    path = tmp_path / "drive" / "a.jpg"
    path.write_bytes(jpeg_with_exif())
    await repo.put_user(ctx.store, USER)
    await ingest.sync(ctx, USER)
    path.rename(tmp_path / "drive" / "renamed.jpg")
    assert await ingest.sync(ctx, USER) == []


async def test_corrupt_file_fails_visibly(tmp_path):
    ctx = make_context(tmp_path)
    (tmp_path / "drive" / "bad.jpg").write_bytes(b"definitely not a jpeg")
    await repo.put_user(ctx.store, USER)
    created = await ingest.sync(ctx, USER)
    with pytest.raises(OSError):  # Pillow: UnidentifiedImageError
        await ingest.ingest(ctx, {"shot_id": created[0].id})
    shot = await repo.get_shot(ctx.store, created[0].id)
    assert shot.status is ShotStatus.FAILED and shot.error


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
async def test_video_becomes_a_contact_sheet(tmp_path):
    ctx = make_context(tmp_path)
    (tmp_path / "drive" / "clip.mp4").write_bytes(two_shot_video())
    await repo.put_user(ctx.store, USER)
    created = await ingest.sync(ctx, USER)
    await ctx.bus.drain()

    shot = await repo.get_shot(ctx.store, created[0].id)
    assert shot.status is ShotStatus.INGESTED and shot.kind is ShotKind.VIDEO
    assert shot.video.fps == 30 and shot.video.width == 320
    assert 3.5 < shot.video.duration_s < 4.5
    assert set(shot.blobs) == {ORIGINAL, SHEET, GRIDDED, THUMB}
    sheet = Image.open(tmp_path / "blobs" / shot.blobs[SHEET])
    assert sheet.width > 480  # at least two tiles: frame 0 and the cut


def test_sample_times_merges_cuts_with_an_even_spread():
    times = ingest.sample_times(10.0, cuts=[0.0, 4.2], minimum=5, maximum=12)
    assert times[0] == 0.0
    assert 4.2 in times
    assert all(t < 10.0 for t in times)
    assert times == sorted(times)
    assert len(times) >= 5


def test_sample_times_caps_and_handles_edge_cases():
    many = ingest.sample_times(60.0, cuts=[float(i) for i in range(60)], minimum=6, maximum=12)
    assert len(many) == 12 and many == sorted(many)
    assert ingest.sample_times(0.0, cuts=[], minimum=6, maximum=12) == [0.0]
    near = ingest.sample_times(10.0, cuts=[2.0, 2.1], minimum=1, maximum=12)
    assert near.count(2.0) == 1 and 2.1 not in near  # deduped to the nearest 0.25s
