"""Real-model story check on isolated copies of stored Shots and Analyses.

Run from backend with --store, --blobs, --shot (repeatable), and --out. Never
writes to the source store or original files. This is not end-to-end ingest proof.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageStat

from app.agents.runtime import MODEL_USAGE_LOG_PREFIX
from app.domain.entities import Analysis, Provenance, ShootReceipt, ShootRecord, Shot, User, now
from app.imaging import canvas
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.storage import ORIGINAL, LocalBlobStore, blob_path, visual_evidence_blob_path
from app.infra.store import FileStore
from app.services import deconstructions
from app.services.context import Context


class UsageCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.entries: list[dict] = []

    def emit(self, record: logging.LogRecord) -> None:
        text = record.getMessage()
        if text.startswith(MODEL_USAGE_LOG_PREFIX):
            self.entries.append(json.loads(text.removeprefix(MODEL_USAGE_LOG_PREFIX)))


def render_previews(report: dict, destination: Path) -> None:
    """Contact sheets for review only; never inserted into the exported carousel."""
    for case in report["cases"]:
        files = case.get("files", [])
        if not files:
            continue
        sheet = Image.new("RGB", (len(files) * 336 + 16, 522), (20, 21, 20))
        draw = ImageDraw.Draw(sheet)
        title = case["draft"]["pages"][0]["title"]
        draw.text(
            (16, 14),
            f"{title} | Model draft, isolated input copy",
            font=canvas.font_for(23),
            fill="white",
        )
        for index, file in enumerate(files):
            frame = canvas.load(file["path"])
            frame = ImageOps.contain(frame, (320, 400), Image.Resampling.LANCZOS)
            x = 16 + index * 336
            sheet.paste(frame, (x + (320 - frame.width) // 2, 62 + (400 - frame.height) // 2))
            label = (
                "Clean Shot" if index == len(files) - 1 else "Opening" if index == 0 else "Story"
            )
            draw.text((x, 484), f"{index + 1}. {label}", font=canvas.font_for(20), fill="white")
        sheet.save(destination / case["source_id"] / "preview.png")


async def check(args: argparse.Namespace) -> int:
    source_path = Path(args.store).resolve()
    original_root = Path(args.blobs).resolve()
    destination = Path(args.out).resolve()
    if destination == original_root or destination == source_path.parent:
        raise ValueError("Output must be an isolated directory, never the source store directory.")
    before = source_path.read_bytes()
    source = json.loads(before)
    destination.mkdir(parents=True, exist_ok=True)
    ctx = Context(
        store=FileStore(destination / "store.json"),
        blobs=LocalBlobStore(destination / "media"),
        bus=InProcessBus(),
        drive=None,
        tokens=None,
    )
    user_id = "deconstruction-quality-copy"
    await repo.put_user(ctx.store, User(id=user_id, email="story-check@example.test"))
    usage = UsageCapture()
    logging.getLogger("app.agents.runtime").addHandler(usage)
    report = {
        "scope": (
            "Real Scribe model calls on isolated copies of existing Shot Analysis; "
            "not an ingest run."
        ),
        "source_store_sha256": hashlib.sha256(before).hexdigest(),
        "cases": [],
    }
    for shot_id in args.shot:
        source_shot = Shot.model_validate(source["shots"][shot_id])
        source_analysis = Analysis.model_validate(source["analyses"][shot_id])
        payload = (original_root / source_shot.blobs[ORIGINAL]).read_bytes()
        original_digest = hashlib.sha256(payload).hexdigest()
        path = blob_path(user_id, shot_id, ORIGINAL, "jpg")
        await ctx.blobs.write(path, payload, source_shot.mime_type)
        shot = source_shot.model_copy(
            update={"user_id": user_id, "kept_at": now(), "blobs": {ORIGINAL: path}}
        )
        await repo.put_shot(ctx.store, shot)
        analysis = source_analysis.model_copy(deep=True, update={"user_id": user_id})
        copied_artifacts = []
        for technique in analysis.techniques:
            artifact = technique.visual_artifact
            if artifact is None or not artifact.blob_path:
                continue
            expected = visual_evidence_blob_path(
                source_shot.user_id, shot_id, technique.technique_id
            )
            if artifact.blob_path != expected:
                continue
            artifact_path = original_root / expected
            copied_path = visual_evidence_blob_path(user_id, shot_id, technique.technique_id)
            artifact.blob_path = copied_path
            if artifact_path.is_file():
                artifact_bytes = artifact_path.read_bytes()
                await ctx.blobs.write(copied_path, artifact_bytes, "image/jpeg")
                copied_artifacts.append(
                    {
                        "technique_id": technique.technique_id,
                        "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
                        "source_path": str(artifact_path),
                    }
                )
        await repo.put_analysis(ctx.store, analysis)
        source_id = f"story_check_{hashlib.sha256(shot_id.encode()).hexdigest()[:12]}"
        record = ShootRecord(
            shoot_id=source_id,
            user_id=user_id,
            revision=1,
            shot_ids=[shot_id],
            receipt=ShootReceipt(
                shot_count=1,
                readable_shot_count=1,
                keeper_shot_ids=[shot_id],
                summary="Isolated story validation copy, not a natural Shoot grouping.",
            ),
            provenance=Provenance(
                shot_ids=[shot_id], sample_size=1, calc_version="isolated-story-quality-check"
            ),
        )
        await repo.put_shoot_record_once(ctx.store, record)
        started = time.monotonic()
        usage_start = len(usage.entries)
        case = {
            "shot_id": shot_id,
            "filename": shot.filename,
            "source_id": source_id,
            "copied_artifacts": copied_artifacts,
        }
        try:
            draft = await deconstructions.prepare(
                ctx, user_id, deconstructions.DeconstructionSourceType.SHOOT, source_id, 1, shot_id
            )
            case["seconds"] = round(time.monotonic() - started, 3)
            case["draft"] = draft.model_dump(mode="json")
            case["artifact_pages"] = sum(page.visual_layer == "artifact" for page in draft.pages)
            case["files"] = []
            for index, page in enumerate(draft.pages, 1):
                data = await ctx.blobs.read(page.blob_path)
                output = destination / source_id / f"{index:02d}-{page.kind.value}.jpg"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(data)
                rendered = canvas.load_bytes(data)
                case["files"].append(
                    {"path": str(output), "width": rendered.width, "height": rendered.height}
                )
                if page.kind.value != "clean":
                    assert rendered.size == (1080, 1350)
                else:
                    original = canvas.load_bytes(payload)
                    assert rendered.size == original.size
                    difference = ImageStat.Stat(ImageChops.difference(original, rendered)).mean
                    assert max(difference) < 6, difference
                    case["clean_mean_pixel_difference"] = difference
            assert draft.pages[-1].kind.value == "clean"
            assert all(page.shot_ids == [shot_id] for page in draft.pages)
            assert hashlib.sha256(await ctx.blobs.read(path)).hexdigest() == original_digest
            for copied in copied_artifacts:
                assert (
                    hashlib.sha256(Path(copied["source_path"]).read_bytes()).hexdigest()
                    == copied["sha256"]
                )
            calls = len(usage.entries)
            retry_at = time.monotonic()
            cached = await deconstructions.prepare(
                ctx, user_id, deconstructions.DeconstructionSourceType.SHOOT, source_id, 1, shot_id
            )
            assert cached.model_dump() == draft.model_dump()
            assert len(usage.entries) == calls
            case["cached_seconds"] = round(time.monotonic() - retry_at, 3)
            case["status"] = "rendered_requires_visual_review"
        except Exception as exc:
            logging.exception("Story quality case failed: %s", shot_id)
            case["status"] = "failed"
            case["error_type"] = type(exc).__name__
            case["error"] = str(exc)
            case["seconds"] = round(time.monotonic() - started, 3)
        case["model_usage"] = usage.entries[usage_start:]
        report["cases"].append(case)
        (destination / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {key: value for key, value in case.items() if key not in {"draft", "model_usage"}}
            ),
            flush=True,
        )
    assert source_path.read_bytes() == before, "The source store changed during the check."
    render_previews(report, destination)
    return int(any(case["status"] == "failed" for case in report["cases"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True)
    parser.add_argument("--blobs", required=True)
    parser.add_argument("--shot", action="append", required=True)
    parser.add_argument("--out", required=True)
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(asyncio.run(check(parser.parse_args())))


if __name__ == "__main__":
    main()
