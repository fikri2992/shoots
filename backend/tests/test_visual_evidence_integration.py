"""Real pixels -> artifact blobs -> authenticated Shot API."""

import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFilter

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    Analysis,
    Exif,
    GridSpec,
    Shot,
    ShotKind,
    ShotStatus,
    TechniqueEvidence,
    User,
    VisualPath,
    VisualPathRole,
)
from app.domain.grid import Grid
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import ORIGINAL, LocalBlobStore, blob_path
from app.infra.store import InMemoryStore
from app.services import analyst
from app.services.context import Context
from scripts import backfill_visual_evidence

ROOT = Path(__file__).resolve().parents[2]


def _visual_fixture() -> tuple[Image.Image, bytes]:
    width, height = 800, 600
    background = Image.new("RGB", (width, height), (18, 35, 50))
    draw = ImageDraw.Draw(background)
    lights = (
        (80, 90, 28, (255, 205, 90)),
        (190, 180, 42, (240, 120, 70)),
        (650, 105, 34, (80, 215, 225)),
        (710, 260, 24, (255, 225, 150)),
        (570, 410, 38, (85, 195, 225)),
    )
    for x, y, radius, colour in lights:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=colour)
    background = background.filter(ImageFilter.GaussianBlur(8))
    draw = ImageDraw.Draw(background)
    draw.rectangle((310, 75, 520, 560), fill=(210, 75, 48))
    for y in range(95, 550, 22):
        draw.line((325, y, 505, y), fill=(255, 220, 190), width=3)
    buffer = io.BytesIO()
    background.save(buffer, format="JPEG", quality=92)
    return background, buffer.getvalue()


def _radial_fixture() -> tuple[Image.Image, bytes]:
    image = Image.new("RGB", (800, 600), (18, 20, 28))
    draw = ImageDraw.Draw(image)
    centre = (400, 300)
    endpoints = [
        (0, 0),
        (200, 0),
        (400, 0),
        (600, 0),
        (799, 0),
        (799, 150),
        (799, 300),
        (799, 450),
        (799, 599),
        (600, 599),
        (400, 599),
        (200, 599),
        (0, 599),
        (0, 450),
        (0, 300),
        (0, 150),
    ]
    for index, endpoint in enumerate(endpoints):
        draw.line((centre, endpoint), fill=(80 + index * 8, 190, 225), width=9)
    image = image.filter(ImageFilter.GaussianBlur(2.2))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return image, buffer.getvalue()


def _leading_path_fixture() -> tuple[Image.Image, bytes]:
    image = Image.new("RGB", (800, 600), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.line((250, 550, 350, 350), fill=(255, 255, 255), width=9)
    draw.line((650, 550, 550, 350), fill=(255, 255, 255), width=9)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return image, buffer.getvalue()


async def test_visual_artifacts_survive_real_blob_and_api_boundaries(tmp_path):
    ctx = Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(tmp_path / "blobs"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user = User(id="visual_user", email="visual@example.test")
    shot = Shot(
        id="visual_shot",
        user_id=user.id,
        kind=ShotKind.PHOTO,
        filename="visual.jpg",
        mime_type="image/jpeg",
        status=ShotStatus.ANALYZED,
        grid=GridSpec(cols=8, rows=6, width=800, height=600),
        exif=Exif(iso=3200, f_number=1.8, exposure_time_s=1 / 60),
    )
    analysis = Analysis(
        shot_id=shot.id,
        user_id=user.id,
        model="gemini-integration",
        techniques=[
            TechniqueEvidence(
                technique_id="complementary",
                confidence=0.9,
                agreement=2,
                cells=[f"{column}{row}" for row in range(1, 7) for column in "ABCDEFGH"],
            ),
            TechniqueEvidence(
                technique_id="shallow_dof",
                confidence=0.9,
                agreement=2,
                cells=["D2", "E2", "D3", "E3", "D4", "E4", "D5", "E5"],
            ),
            TechniqueEvidence(
                technique_id="bokeh_balls",
                confidence=0.9,
                agreement=2,
                cells=[f"{column}{row}" for row in range(1, 7) for column in "ABCDEFGH"],
            ),
            TechniqueEvidence(
                technique_id="fill_the_frame",
                confidence=0.9,
                agreement=2,
                cells=["D2", "E2", "F2", "D3", "E3", "F3", "D4", "E4", "F4", "D5", "E5", "F5"],
            ),
        ],
    )
    image, source_bytes = _visual_fixture()
    await analyst.render_visual_evidence(ctx, shot, analysis, image, source_bytes)
    await repo.put_user(ctx.store, user)
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(ctx.store, analysis)

    artifacts = {item.technique_id: item.visual_artifact for item in analysis.techniques}
    assert artifacts["complementary"].kind.value == "hue_mask"
    assert artifacts["shallow_dof"].kind.value == "sharpness_map"
    assert artifacts["bokeh_balls"].kind.value == "bokeh_instances"
    assert artifacts["fill_the_frame"].kind.value == "subject_contour"
    assert all(item and item.blob_path for item in artifacts.values())

    path_image, path_bytes = _leading_path_fixture()
    path_shot = shot.model_copy(update={"id": "path_shot", "filename": "path.jpg"})
    path_analysis = Analysis(
        shot_id=path_shot.id,
        user_id=user.id,
        model="gemini-integration",
        techniques=[
            TechniqueEvidence(
                technique_id="leading_lines",
                confidence=0.9,
                agreement=2,
                cells=["C6", "D4", "G6", "F4"],
                paths=[
                    VisualPath(
                        points=["C6", "D4"],
                        leads_to=["E2"],
                        role=VisualPathRole.BOUNDARY,
                    ),
                    VisualPath(
                        points=["G6", "F4"],
                        leads_to=["E2"],
                        role=VisualPathRole.BOUNDARY,
                    ),
                ],
            )
        ],
    )
    await analyst.render_visual_evidence(
        ctx,
        path_shot,
        path_analysis,
        path_image,
        path_bytes,
    )
    path_artifact = path_analysis.techniques[0].visual_artifact
    assert path_artifact.kind.value == "verified_paths"
    assert path_artifact.metrics["path_count"] == 2
    rendered_path = Image.open(io.BytesIO(await ctx.blobs.read(path_artifact.blob_path))).convert(
        "RGB"
    )
    connector_patch = rendered_path.crop((394, 244, 407, 257))
    assert max(maximum for _, maximum in connector_patch.getextrema()) > 80

    radial_image, radial_bytes = _radial_fixture()
    radial_shot = shot.model_copy(update={"id": "radial_shot", "filename": "radial.jpg"})
    radial_analysis = Analysis(
        shot_id=radial_shot.id,
        user_id=user.id,
        model="gemini-integration",
        techniques=[
            TechniqueEvidence(
                technique_id="zoom_burst",
                confidence=0.9,
                agreement=2,
                cells=[f"{column}{row}" for row in range(1, 7) for column in "ABCDEFGH"],
            )
        ],
    )
    await analyst.render_visual_evidence(
        ctx,
        radial_shot,
        radial_analysis,
        radial_image,
        radial_bytes,
    )
    radial_artifact = radial_analysis.techniques[0].visual_artifact
    assert radial_artifact.kind.value == "radial_blur"
    assert await ctx.blobs.exists(radial_artifact.blob_path)

    face_path = ROOT / "docs/test-corpus/online-inspiration/03-window-portrait.jpg"
    with Image.open(face_path) as opened:
        face_image = opened.convert("RGB")
    face_grid = Grid.for_image(*face_image.size)
    face_shot = shot.model_copy(
        update={
            "id": "face_shot",
            "filename": face_path.name,
            "grid": GridSpec(
                cols=face_grid.cols,
                rows=face_grid.rows,
                width=face_image.width,
                height=face_image.height,
            ),
        }
    )
    face_analysis = Analysis(
        shot_id=face_shot.id,
        user_id=user.id,
        model="gemini-integration",
        techniques=[
            TechniqueEvidence(
                technique_id="eye_contact_portrait",
                confidence=0.9,
                agreement=2,
                cells=face_grid.all_refs(),
            )
        ],
    )
    await analyst.render_visual_evidence(
        ctx,
        face_shot,
        face_analysis,
        face_image,
        face_path.read_bytes(),
    )
    face_artifact = face_analysis.techniques[0].visual_artifact
    assert face_artifact.kind.value == "face_landmarks"
    assert face_artifact.metrics["eye_count"] == 2

    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": user.id}
    try:
        with TestClient(main.app) as client:
            response = client.get(f"/api/shots/{shot.id}")
            assert response.status_code == 200
            techniques = response.json()["analysis"]["techniques"]
            bokeh = next(item for item in techniques if item["technique_id"] == "bokeh_balls")
            path = bokeh["visual_artifact"]["blob_path"]
            blob = client.get(f"/api/blobs/{path}")
            assert blob.status_code == 200
            assert blob.headers["content-type"] == "image/jpeg"
            assert len(blob.content) > 1000
            teaching = response.json()["teaching"]
            assert teaching["keep_mark"]["visual_artifact"]["blob_path"]
    finally:
        main.app.dependency_overrides.clear()

    old_shot = shot.model_copy(
        update={
            "id": "old_visual_shot",
            "filename": "old-visual.jpg",
            "blobs": {
                ORIGINAL: await ctx.blobs.write(
                    blob_path(user.id, "old_visual_shot", ORIGINAL, "jpg"),
                    source_bytes,
                    "image/jpeg",
                )
            },
        }
    )
    old_analysis = Analysis(
        shot_id=old_shot.id,
        user_id=user.id,
        model="gemini-before-visual-artifacts",
        techniques=[
            TechniqueEvidence(
                technique_id="complementary",
                confidence=0.9,
                agreement=2,
                cells=[f"{column}{row}" for row in range(1, 7) for column in "ABCDEFGH"],
            )
        ],
    )
    await repo.put_shot(ctx.store, old_shot)
    await repo.put_analysis(ctx.store, old_analysis)
    first_backfill = await backfill_visual_evidence.run(user.id, context=ctx)
    assert first_backfill["updated"] == 1
    stored = await repo.find_analysis(ctx.store, old_shot.id)
    assert stored.techniques[0].visual_artifact.kind.value == "hue_mask"
    second_backfill = await backfill_visual_evidence.run(user.id, context=ctx)
    assert second_backfill["updated"] == 0
    assert second_backfill["skipped"] == 2
