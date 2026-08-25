"""Scribe on a real store, real blobs and a real folder on disk."""

import tempfile
from pathlib import Path

from PIL import Image

from app.domain.entities import (
    Analysis,
    Composition,
    Criteria,
    ExifRule,
    GridSpec,
    Move,
    Quest,
    Shot,
    ShotKind,
    ShotStatus,
    TechniqueEvidence,
    User,
    Verdict,
)
from app.imaging import canvas
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.drive import LocalDriveClient
from app.infra.secrets import LocalTokenStore
from app.infra.storage import ANNOTATED, LocalBlobStore, blob_path
from app.infra.store import InMemoryStore
from app.services import scribe
from app.services.context import Context


async def seed(folder: str, with_verdict: bool) -> Context:
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(folder),
        bus=InProcessBus(),
        drive=LocalDriveClient(folder),
        tokens=LocalTokenStore(folder),
    )
    await repo.put_user(ctx.store, User(id="u1", email="u@x", drive_folder_id="local"))
    shot = Shot(
        id="shot_1",
        user_id="u1",
        drive_file_id="f1",
        filename="bike.jpg",
        mime_type="image/jpeg",
        kind=ShotKind.PHOTO,
        status=ShotStatus.ANALYZED,
        grid=GridSpec(cols=8, rows=6, width=800, height=600),
        quest_id="quest_1" if with_verdict else "",
    )
    frame = Image.new("RGB", (800, 600), (30, 90, 140))
    shot.blobs[ANNOTATED] = await ctx.blobs.write(
        blob_path("u1", shot.id, ANNOTATED, "jpg"), canvas.to_jpeg_bytes(frame), "image/jpeg"
    )
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id="shot_1",
            user_id="u1",
            model="m",
            techniques=[TechniqueEvidence(technique_id="panning", confidence=0.9, note="blur")],
            composition=Composition(
                moves=[Move(what="rider", from_cells=["C3"], to_cells=["E3"], reason="lead room")]
            ),
            critique="Background streaks well; the rider is too central.",
            score=7,
        ),
    )
    if with_verdict:
        await repo.put_quest(
            ctx.store,
            Quest(
                id="quest_1",
                user_id="u1",
                technique_id="panning",
                title="Follow the rider",
                brief="1. Pan.",
                why_now="",
                criteria=Criteria(exif=ExifRule(), vision=["panning"], text=["streaks"]),
                verdicts=[
                    Verdict(shot_id="shot_1", passed=True, feedback="Clean pan. Next: slower.")
                ],
            ),
        )
    return ctx


async def test_review_lands_in_the_folder_with_caption_and_verdict():
    with tempfile.TemporaryDirectory() as folder:
        ctx = await seed(folder, with_verdict=True)
        publisher = scribe.LocalReviewPublisher(folder)
        file_id = await scribe.write_review(ctx, {"shot_id": "shot_1"}, publisher)
        assert file_id == "Reviewed/✔ bike — panning.jpg"
        path = Path(folder) / file_id
        assert path.exists()
        with Image.open(path) as image:
            assert image.height > 600  # the caption band was added
        sidecar = path.with_suffix(".txt").read_text(encoding="utf-8")
        assert sidecar.startswith("PASSED · Follow the rider")
        # Places, not coordinates: the reader has no grid in front of them.
        assert "rider: the left of the frame → the centre of the frame" in sidecar
        assert "Clean pan." in sidecar and "C3" not in sidecar

        shot = await repo.get_shot(ctx.store, "shot_1")
        assert shot.drive_review_id == file_id and shot.drive_review_url.endswith(file_id)
        user = await repo.get_user(ctx.store, "u1")
        assert user.drive_review_folder_id == "Reviewed"
        stages = [e.stage for e in await repo.list_events(ctx.store, "u1")]
        assert stages == ["reviewed"]

        # Redelivery updates in place, no second file.
        again = await scribe.write_review(ctx, {"shot_id": "shot_1"}, publisher)
        assert again == file_id
        assert len(list((Path(folder) / "Reviewed").glob("*.jpg"))) == 1


async def test_review_without_quest_has_no_mark():
    with tempfile.TemporaryDirectory() as folder:
        ctx = await seed(folder, with_verdict=False)
        file_id = await scribe.write_review(
            ctx, {"shot_id": "shot_1"}, scribe.LocalReviewPublisher(folder)
        )
        assert file_id == "Reviewed/bike — panning.jpg"
        text = (Path(folder) / file_id).with_suffix(".txt").read_text(encoding="utf-8")
        assert text.startswith("Panning")


async def test_unanalysed_shot_is_skipped():
    with tempfile.TemporaryDirectory() as folder:
        ctx = await seed(folder, with_verdict=False)
        shot = await repo.get_shot(ctx.store, "shot_1")
        shot.status = ShotStatus.INGESTED
        await repo.put_shot(ctx.store, shot)
        assert (
            await scribe.write_review(
                ctx, {"shot_id": "shot_1"}, scribe.LocalReviewPublisher(folder)
            )
            is None
        )
