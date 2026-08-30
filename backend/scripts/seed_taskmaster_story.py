"""Build one isolated, read-only local web interface fixture.

No agent runs in this script. Every generated record is hand-authored and the
account is marked as a Sample Record so authenticated writes are refused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageOps

from app.domain.entities import (
    ActivityEvent,
    Analysis,
    Composition,
    EvidenceAuthority,
    GridSpec,
    JourneyUpdate,
    ModelProvenance,
    Provenance,
    RecordMode,
    Run,
    RunStatus,
    RunStep,
    RunStepState,
    Scene,
    ScoutDecision,
    ScoutRejectedRoute,
    Shoot,
    ShootDimensionFigure,
    ShootReceipt,
    ShootRecord,
    ShootStatus,
    ShootTechniqueFigure,
    Shot,
    ShotKind,
    ShotSource,
    ShotStatus,
    TechniqueEvidence,
    TechniqueState,
    TechniqueStatus,
    User,
    VisualArtifactAuthority,
    VisualPath,
    VisualPathRole,
    VisualRegion,
    VisualRegionRole,
)
from app.imaging import tone as tone_image
from app.imaging import visual_evidence
from app.imaging.exif import read_exif
from app.infra.storage import visual_evidence_blob_path

USER_ID = "dev:preview@shoots.local"
SHOOT_ID = "shoot_ridge_sunrise"
FILES = (
    ("IMG_20251206_052515.jpg", "2025-12-06T05:25:15+07:00", "scene_road_to_ridge"),
    ("IMG_20251206_052517.jpg", "2025-12-06T05:25:17+07:00", "scene_road_to_ridge"),
    ("IMG_20251206_052520.jpg", "2025-12-06T05:25:20+07:00", "scene_road_to_ridge"),
    ("IMG_20251206_052523.jpg", "2025-12-06T05:25:23+07:00", "scene_road_to_ridge"),
    ("IMG_20251206_052526.jpg", "2025-12-06T05:25:26+07:00", "scene_road_to_ridge"),
    ("IMG_20251206_053304.jpg", "2025-12-06T05:33:04+07:00", "scene_valley_overlook"),
    ("IMG_20251206_054812.jpg", "2025-12-06T05:48:12+07:00", "scene_open_ridge"),
    ("IMG_20251206_054815.jpg", "2025-12-06T05:48:15+07:00", "scene_open_ridge"),
    ("IMG_20251206_054817.jpg", "2025-12-06T05:48:17+07:00", "scene_open_ridge"),
    ("IMG_20251206_054820.jpg", "2025-12-06T05:48:20+07:00", "scene_open_ridge"),
)


def _dump(value: object) -> dict:
    return value.model_dump(mode="json")  # type: ignore[attr-defined]


def _shot_id(index: int) -> str:
    return f"shot_ridge_{index:02d}"


def _run_step(state: RunStepState, outcome: str, at: datetime) -> RunStep:
    return RunStep(state=state, outcome=outcome, settled_at=at)


def _thumb(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        image.thumbnail((960, 960), Image.Resampling.LANCZOS)
        image.save(target, "JPEG", quality=86, optimize=True)


def _layering_regions(*, landscape: bool) -> list[VisualRegion]:
    """Human-reviewed depth bands for this fixed ridge fixture."""
    foreground_rows = (6,) if landscape else (5, 6)
    bands = (
        (VisualRegionRole.FOREGROUND, foreground_rows),
        (VisualRegionRole.MIDGROUND, (5,) if landscape else (4,)),
        (VisualRegionRole.BACKGROUND, (4,) if landscape else (3,)),
    )
    return [
        VisualRegion(
            cells=[f"{column}{row}" for row in rows for column in "ABCDEFGH"],
            role=role,
            order=order,
        )
        for order, (role, rows) in enumerate(bands)
    ]


def _road_paths(index: int) -> list[VisualPath]:
    """Human-reviewed road boundaries for one of the first three ridge Shots."""
    target = ["E4"]
    right_boundary = {
        1: ["H6", "G5", "F4"],
        2: ["H6", "G5", "F4"],
        3: ["H6", "H5", "G4"],
    }[index]
    return [
        VisualPath(
            points=["D6", "D5", "E4"],
            leads_to=target,
            role=VisualPathRole.BOUNDARY,
        ),
        VisualPath(
            points=right_boundary,
            leads_to=target,
            role=VisualPathRole.BOUNDARY,
        ),
    ]


def build(source_root: Path, blob_root: Path) -> None:
    missing = [name for name, _, _ in FILES if not (source_root / name).is_file()]
    if missing:
        raise SystemExit(f"Missing source files: {', '.join(missing)}")

    user = User(
        id=USER_ID,
        email="preview@shoots.local",
        name="Sample Record",
        record_mode=RecordMode.SAMPLE,
    )
    encoded_user = quote(USER_ID, safe="")
    shots: list[Shot] = []
    analyses: list[Analysis] = []
    runs: list[Run] = []
    scene_members: dict[str, list[str]] = {
        "scene_road_to_ridge": [],
        "scene_valley_overlook": [],
        "scene_open_ridge": [],
    }

    for index, (filename, captured_text, scene_id) in enumerate(FILES, start=1):
        source = source_root / filename
        data = source.read_bytes()
        captured = datetime.fromisoformat(captured_text)
        shot_id = _shot_id(index)
        shot_dir = blob_root / "users" / encoded_user / "shots" / shot_id
        shot_dir.mkdir(parents=True, exist_ok=True)
        original = shot_dir / "original.jpg"
        thumb = shot_dir / "thumb.jpg"
        shutil.copyfile(source, original)
        _thumb(source, thumb)

        with Image.open(source) as opened:
            width, height = opened.size
            measured_tone = tone_image.measure(ImageOps.exif_transpose(opened))
        exif = read_exif(data).model_copy(
            update={"captured_at": captured, "latitude": None, "longitude": None}
        )
        relative = f"users/{encoded_user}/shots/{shot_id}"
        shot = Shot(
            id=shot_id,
            user_id=USER_ID,
            kind=ShotKind.PHOTO,
            source=ShotSource.WEB_UPLOAD,
            source_id=f"sample-fixture:{filename}",
            filename=filename,
            mime_type="image/jpeg",
            status=ShotStatus.ANALYZED,
            exif=exif,
            tone=measured_tone,
            grid=GridSpec(cols=8, rows=6, width=width, height=height),
            blobs={"original": f"{relative}/original.jpg", "thumb": f"{relative}/thumb.jpg"},
            captured_at=captured,
            ingested_at=captured + timedelta(seconds=8),
            analyzed_at=captured + timedelta(seconds=28),
        )
        shots.append(shot)
        scene_members[scene_id].append(shot_id)

        road_scene = scene_id == "scene_road_to_ridge"
        shows_road_lines = road_scene and index <= 3
        layering_regions = _layering_regions(landscape=width > height)
        techniques = [
            TechniqueEvidence(
                technique_id="layering",
                confidence=0.86,
                cells=list(
                    dict.fromkeys(cell for region in layering_regions for cell in region.cells)
                ),
                regions=layering_regions,
                note="Near structures, cloud, and distant ridge create three depth planes.",
                agreement=3,
                lenses=["manual_fixture_layout", "manual_fixture_copy", "manual_fixture_review"],
            )
        ]
        if shows_road_lines:
            road_paths = _road_paths(index)
            road_evidence = TechniqueEvidence(
                technique_id="leading_lines",
                confidence=0.84,
                cells=list(
                    dict.fromkeys(
                        cell for path in road_paths for cell in (*path.points, *path.leads_to)
                    )
                ),
                paths=road_paths,
                note="The two road boundaries narrow toward the distant ridge.",
                agreement=3,
                lenses=["manual_fixture_layout", "manual_fixture_copy", "manual_fixture_review"],
            )
            with Image.open(source) as opened:
                rendered = visual_evidence.render(
                    ImageOps.exif_transpose(opened),
                    shot,
                    road_evidence,
                    hashlib.sha256(data).hexdigest()[:24],
                )
            artifact = rendered.artifact
            artifact.authority = VisualArtifactAuthority.MANUAL_FIXTURE
            if artifact.metrics.get("path_count") != len(road_paths):
                raise RuntimeError(
                    f"{shot_id}: only {artifact.metrics.get('path_count', 0)} of "
                    f"{len(road_paths)} reviewed leading paths reached visible edges"
                )
            if rendered.image is not None:
                artifact.blob_path = visual_evidence_blob_path(
                    USER_ID,
                    shot_id,
                    road_evidence.technique_id,
                )
                artifact_file = blob_root / artifact.blob_path
                artifact_file.parent.mkdir(parents=True, exist_ok=True)
                rendered.image.save(artifact_file, "JPEG", quality=88, optimize=True)
            road_evidence.visual_artifact = artifact
            techniques.append(road_evidence)
        critique = (
            "The road carries the eye toward the cloud-filled ridge while the sky remains dominant."
            if road_scene
            else (
                "The wider view lets the cloud and ridge layers carry the scene "
                "while the foreground recedes."
            )
        )
        analyses.append(
            Analysis(
                shot_id=shot_id,
                user_id=USER_ID,
                model="manual_fixture",
                prompt_version="hand-authored-interface-fixture-1",
                techniques=techniques,
                composition=Composition(
                    subject_cells=["D3", "E3", "D4"],
                    subject_x=0.5,
                    subject_y=0.58,
                    guide="thirds",
                ),
                observations=[
                    "A distant ridge divides the cloud layer from the bright sky.",
                    (
                        "A dark road or path enters from the foreground."
                        if road_scene
                        else "The frame opens horizontally across the ridge and clouds."
                    ),
                ],
                critique=critique,
                panel={},
                created_at=captured + timedelta(seconds=24),
            )
        )

        completed = captured + timedelta(seconds=32)
        runs.append(
            Run(
                id=f"run_{shot_id}",
                user_id=USER_ID,
                shot_id=shot_id,
                source=ShotSource.WEB_UPLOAD,
                status=RunStatus.COMPLETED,
                steps={
                    "ingest": _run_step(
                        RunStepState.COMPLETED, "Sample fixture; Ingest did not run", completed
                    ),
                    "analyst": _run_step(
                        RunStepState.COMPLETED, "Sample fixture; Analyst did not run", completed
                    ),
                    "cartographer": _run_step(
                        RunStepState.COMPLETED,
                        "Sample fixture; Cartographer did not run",
                        completed,
                    ),
                    "judge": _run_step(
                        RunStepState.SKIPPED, "Sample fixture; Judge did not run", completed
                    ),
                    "scribe": _run_step(
                        RunStepState.SKIPPED, "Sample fixture; Scribe did not run", completed
                    ),
                    "scout": _run_step(
                        RunStepState.COMPLETED, "Sample fixture; Scout did not run", completed
                    ),
                },
                started_at=captured + timedelta(seconds=8),
                updated_at=completed,
                completed_at=completed,
            )
        )

    scene_times = {
        "scene_road_to_ridge": (FILES[0][1], FILES[4][1]),
        "scene_valley_overlook": (FILES[5][1], FILES[5][1]),
        "scene_open_ridge": (FILES[6][1], FILES[9][1]),
    }
    scenes = [
        Scene(
            id=scene_id,
            user_id=USER_ID,
            shoot_id=SHOOT_ID,
            ordered_shot_ids=ids,
            started_at=datetime.fromisoformat(scene_times[scene_id][0]),
            ended_at=datetime.fromisoformat(scene_times[scene_id][1]),
        )
        for scene_id, ids in scene_members.items()
    ]
    shot_ids = [shot.id for shot in shots]
    scene_ids = [scene.id for scene in scenes]
    settled_at = datetime.fromisoformat("2025-12-06T06:20:00+07:00")
    shoot = Shoot(
        id=SHOOT_ID,
        user_id=USER_ID,
        status=ShootStatus.SETTLED,
        revision=1,
        current_record_revision=1,
        ordered_scene_ids=scene_ids,
        ordered_shot_ids=shot_ids,
        started_at=shots[0].captured_at,
        last_capture_at=shots[-1].captured_at,
        closed_at=settled_at,
    )

    summary = (
        "The distant ridge and cloud layer remain the anchor across three Scenes, "
        "while the amount of foreground changes."
    )
    receipt = ShootReceipt(
        calc_version="sample-interface-fixture-1",
        summary=summary,
        shot_count=len(shots),
        scene_count=len(scenes),
        shots_per_scene=[len(scene.ordered_shot_ids) for scene in scenes],
        readable_shot_count=len(shots),
        repeated=["The distant ridge and cloud layer remain the visual anchor in all 10 Shots."],
        varied=[
            "The first Scene uses the road as an entry; later Scenes open into "
            "wider horizontal layers.",
            "Six portrait Shots become four landscape Shots.",
        ],
        blind_spots=[
            "One Shoot shows repetition, not whether the choice was deliberate.",
            (
                "When this Shoot settled, no Keeper mark had been made, so this record "
                "does not claim which Shots you valued then."
            ),
        ],
        dimensions=[
            ShootDimensionFigure(
                dimension_id="orientation",
                label="how you hold the camera",
                authority=EvidenceAuthority.MEASURED,
                counts={"portrait": 6, "landscape": 4},
                readable_shots=10,
                dominant="portrait",
                dominant_count=6,
            )
        ],
        techniques=[
            ShootTechniqueFigure(
                technique_id="layering",
                name="Layering",
                observed_shot_ids=shot_ids,
                corroborated_shot_ids=shot_ids,
            ),
            ShootTechniqueFigure(
                technique_id="leading_lines",
                name="Leading lines",
                observed_shot_ids=shot_ids[:3],
                corroborated_shot_ids=shot_ids[:3],
            ),
        ],
    )
    scout = ScoutDecision(
        route="explain",
        reason=(
            "A clear visual thread runs through this outing. It is worth seeing without "
            "turning it into homework."
        ),
        rejected_routes=[
            ScoutRejectedRoute(
                route="reproduce",
                reason="No marked Shot says which choice you want to repeat yet.",
            )
        ],
        input_shot_ids=shot_ids,
        policy_version="shoot-scout-1",
        execution_state="completed",
        executed_at=settled_at,
        decided_at=settled_at,
    )
    provenance = Provenance(
        shot_ids=shot_ids,
        sample_size=len(shots),
        calc_version="sample-interface-fixture-1",
        model="manual_fixture",
        prompt_version="hand-authored-interface-fixture-1",
        inputs=[
            ModelProvenance(
                model="manual_fixture",
                prompt_version="hand-authored-interface-fixture-1",
            )
        ],
    )
    record = ShootRecord(
        shoot_id=SHOOT_ID,
        user_id=USER_ID,
        revision=1,
        scene_ids=scene_ids,
        shot_ids=shot_ids,
        run_outcomes={shot_id: "completed" for shot_id in shot_ids},
        receipt=receipt,
        scout=scout,
        provenance=provenance,
        settled_at=settled_at,
    )
    journey = JourneyUpdate(
        id="journey_ridge_baseline",
        user_id=USER_ID,
        body=(
            "Sample story: across this hand-authored outing, the distant ridge and "
            "cloud layer recur while "
            "foreground paths and open space change how the view is carried. Six "
            "portrait Shots became four landscape Shots. That is a repeated choice in this "
            "record, not proof that you can reproduce it deliberately."
        ),
        evidence=[
            "Fixture layout contains 10 Shots.",
            "Fixture grouping contains three Scenes with 5, 1, and 4 Shots.",
            "Orientation changed from six portrait Shots to four landscape Shots.",
            "You have not marked a Shot yet, so Shoots does not guess which ones matter to you.",
        ],
        counts={"orientation": {"portrait": 6, "landscape": 4}},
        became_recurring=["layering", "leading_lines"],
        shots=10,
        taste_is_known=False,
        keepers=0,
        provenance=provenance,
        created_at=settled_at + timedelta(seconds=8),
    )

    technique_states = []
    for technique_id, ids, distinct_scenes, last_observed in (
        ("layering", shot_ids, 3, shots[-1].captured_at),
        ("leading_lines", shot_ids[:3], 1, shots[2].captured_at),
    ):
        digest = hashlib.sha256("|".join(ids).encode()).hexdigest()[:16]
        technique_states.append(
            TechniqueState(
                user_id=USER_ID,
                technique_id=technique_id,
                status=TechniqueStatus.RECURRING,
                attempts=len(ids),
                corroborated=len(ids),
                best_confidence=0.86,
                last_observed=last_observed,
                shot_ids=ids,
                sightings=len(ids),
                corroborated_shots=len(ids),
                distinct_scenes=distinct_scenes,
                distinct_shoots=1,
                projection_version="technique-map-4",
                input_digest=digest,
            )
        )

    events = [
        ActivityEvent(
            id=f"event_run_{index:02d}",
            user_id=USER_ID,
            agent="fixture",
            stage="sample_loaded",
            detail={"agent_ran": False, "external_write": False},
            shot_id=shot.id,
            at=run.completed_at,
        )
        for index, (shot, run) in enumerate(zip(shots, runs, strict=True), start=1)
    ]
    events.extend(
        [
            ActivityEvent(
                id="event_scout_explained",
                user_id=USER_ID,
                agent="fixture",
                stage="sample_loaded",
                detail={"agent_ran": False, "reason": "Hand-authored Scout layout fixture."},
                at=settled_at + timedelta(seconds=2),
            ),
            ActivityEvent(
                id="event_shoot_settled",
                user_id=USER_ID,
                agent="fixture",
                stage="sample_loaded",
                detail={"agent_ran": False, "external_write": False},
                at=settled_at + timedelta(seconds=1),
            ),
        ]
    )

    store = {
        "users": {user.id: _dump(user)},
        "shots": {shot.id: _dump(shot) for shot in shots},
        "analyses": {analysis.shot_id: _dump(analysis) for analysis in analyses},
        "scenes": {scene.id: _dump(scene) for scene in scenes},
        "shoots": {shoot.id: _dump(shoot)},
        "shoot_records": {f"{SHOOT_ID}__r1": _dump(record)},
        "events": {event.id: _dump(event) for event in events},
        "skills": {
            f"{state.user_id}__{state.technique_id}": _dump(state) for state in technique_states
        },
        "runs": {run.id: _dump(run) for run in runs},
        "journey": {journey.id: _dump(journey)},
        "open_experiments": {},
        "experiments": {},
    }
    blob_root.mkdir(parents=True, exist_ok=True)
    target = blob_root / "store.json"
    target.write_text(json.dumps(store, separators=(",", ":")), encoding="utf-8")
    print(
        f"Wrote a read-only hand-authored Sample Record with {len(shots)} Shot layouts, "
        f"{len(scenes)} Scene layouts, and 1 Shoot Record layout in {target}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--blob-root", type=Path, required=True)
    args = parser.parse_args()
    build(args.source.resolve(), args.blob_root.resolve())


if __name__ == "__main__":
    main()
