"""Run the real Shot learning path against a labelled local corpus.

    uv run python scripts/check_learning_quality.py ../eval/learning-quality.local.json

The manifest supplies only claims a human is willing to label. This script runs the
actual Ingest and Analyst stages, builds the deterministic Shot Teaching Receipt,
saves inspectable artifacts and a versioned JSON report, and exits non-zero when a
declared expectation fails. Human-review items never pretend to be automatic checks.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import mimetypes
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.config import settings
from app.domain import shot_teaching, taxonomy
from app.domain.entities import Analysis, MoveKind, Shot, ShotTeachingReceipt, User
from app.domain.grid import Grid
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.drive import DriveFile
from app.infra.secrets import LocalTokenStore
from app.infra.storage import ANNOTATED, CROP, FINDING_MARKED, LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import analyst, ingest, runs
from app.services.context import Context

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "eval" / "output"
CELL_REF = re.compile(r"\b[A-Z]\d{1,2}\b")
GRID_JARGON = re.compile(
    r"\b(?:cell|cells|row|rows|column|columns|marked area)\b",
    re.IGNORECASE,
)
# ``A`` and ``I`` are ordinary English words, while ``K`` is a temperature unit.
# The active still-image quality grids use at most A-J, so only the remaining
# standalone letters can be leaked internal column labels.
BARE_GRID_COLUMN = re.compile(r"\b[B-HJ]\b")
DANGLING_CONNECTOR = re.compile(r"\b(?:while|and|but|because)\s+the\s+[A-Za-z-]+\.$")
ORPHAN_LOCATOR = re.compile(
    r"\b(?:in|at|from|across|along|into|within)\s+"
    r"(?:is|are|was|were|shows?|exhibits?|remains?)\b",
    re.IGNORECASE,
)
ORPHAN_PREPOSITION_PAIR = re.compile(
    r"\b(?:at|in|within)\s+"
    r"(?:on|beneath|above|below|behind|before|after|against)\b",
    re.IGNORECASE,
)
DANGLING_PARTICIPLE = re.compile(
    r"\b(?:running|spanning|stretching)\s*(?:across|along)?\.$",
    re.IGNORECASE,
)
QUALITY_VERSION = "learning-quality-v1"


class Expectations(BaseModel):
    """Only labels the corpus author can defend for this exact Shot."""

    required_any_techniques: list[list[str]] = Field(default_factory=list)
    forbidden_techniques: list[str] = Field(default_factory=list)
    required_findings: list[str] = Field(default_factory=list)
    forbidden_findings: list[str] = Field(default_factory=list)
    acceptable_move_kinds: list[MoveKind] = Field(default_factory=list)
    forbidden_move_kinds: list[MoveKind] = Field(default_factory=list)
    forbidden_move_phrases: list[str] = Field(default_factory=list)
    acceptable_primary_layers: list[Literal["clean", "finding", "action", "guide"]] = (
        Field(default_factory=list)
    )
    allow_abstention: bool = True
    require_action: bool = False
    expected_subject_box: tuple[float, float, float, float] | None = None
    minimum_subject_iou: float = Field(default=0.25, ge=0, le=1)
    max_visible_characters: int = Field(default=700, ge=80, le=2000)
    human_review: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_labels(self) -> Expectations:
        technique_ids = {
            item
            for group in self.required_any_techniques
            for item in group
        } | set(self.forbidden_techniques)
        unknown = sorted(technique_ids - taxonomy.BY_ID.keys())
        if unknown:
            raise ValueError(f"unknown Technique ids: {unknown}")
        for group in self.required_any_techniques:
            if not group:
                raise ValueError("required_any_techniques groups cannot be empty")
        if self.expected_subject_box is not None:
            left, top, right, bottom = self.expected_subject_box
            if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
                raise ValueError("expected_subject_box must be normalized left, top, right, bottom")
        return self


class QualityCase(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    path: str
    note: str = ""
    expectations: Expectations = Field(default_factory=Expectations)


class QualityManifest(BaseModel):
    name: str
    cases: list[QualityCase] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_case_ids(self) -> QualityManifest:
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("quality case ids must be unique")
        return self


class FileDrive:
    """One immutable local file behind the same download seam Ingest uses."""

    def __init__(self, file_id: str, path: Path):
        self.file_id = file_id
        self.path = path

    async def list_media(self, folder_id: str) -> list[DriveFile]:
        return []

    async def download(self, file_id: str) -> bytes:
        if file_id != self.file_id:
            raise FileNotFoundError(file_id)
        return await asyncio.to_thread(self.path.read_bytes)

    async def watch(self, *args, **kwargs):
        return None

    async def stop(self, *args, **kwargs) -> None:
        return None


def _mime(path: Path) -> str:
    known = {
        ".avif": "image/avif",
        ".heic": "image/heic",
        ".heif": "image/heif",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
    }
    return mimetypes.guess_type(path.name)[0] or known.get(path.suffix.lower(), "")


def _source_path(manifest_path: Path, case: QualityCase) -> Path:
    path = Path(case.path).expanduser()
    if not path.is_absolute():
        path = manifest_path.parent / path
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{case.id}: media not found: {path}")
    if not _mime(path).startswith(("image/", "video/")):
        raise ValueError(f"{case.id}: unsupported media suffix: {path.suffix}")
    return path


async def _read_case(
    manifest_path: Path,
    case: QualityCase,
    asset_root: Path,
) -> tuple[Shot, Analysis, ShotTeachingReceipt, dict[str, str], str, float]:
    path = _source_path(manifest_path, case)
    data = await asyncio.to_thread(path.read_bytes)
    digest = hashlib.sha256(data).hexdigest()
    file_id = f"quality_{digest[:24]}"
    user = User(id=f"quality_{case.id}", email=f"{case.id}@quality.local")
    store = InMemoryStore()
    blobs = LocalBlobStore(asset_root)
    ctx = Context(
        store=store,
        blobs=blobs,
        bus=InProcessBus(),
        drive=FileDrive(file_id, path),
        tokens=LocalTokenStore(asset_root / "tokens"),
    )
    await repo.put_user(store, user)
    drive_file = DriveFile(
        id=file_id,
        name=path.name,
        mime_type=_mime(path),
        size=len(data),
        modified_at=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
    )
    shot = ingest.new_shot(repo.shot_id_for(user.id, file_id), user.id, drive_file)
    await repo.put_shot(store, shot)
    await runs.ensure(ctx, shot)

    started = time.monotonic()
    await ingest.ingest(ctx, {"shot_id": shot.id})
    shot = await repo.get_shot(store, shot.id)
    if shot.status.value == "failed":
        raise RuntimeError(shot.error or "Ingest ended terminally")
    await analyst.analyse(ctx, {"shot_id": shot.id})
    elapsed = time.monotonic() - started

    shot = await repo.get_shot(store, shot.id)
    analysis = await repo.find_analysis(store, shot.id)
    if analysis is None:
        raise RuntimeError(f"Analyst left Shot in {shot.status.value} without Analysis")
    receipt = shot_teaching.build(shot, analysis)
    artifacts = {
        key: str((asset_root / value).resolve())
        for key, value in shot.blobs.items()
        if key in {ANNOTATED, FINDING_MARKED, CROP}
    }
    return shot, analysis, receipt, artifacts, digest, elapsed


def _check(name: str, passed: bool, detail: str) -> dict:
    return {"name": name, "status": "pass" if passed else "fail", "detail": detail}


def _review(name: str, detail: str) -> dict:
    return {"name": name, "status": "review", "detail": detail}


def _visible_text(receipt: ShotTeachingReceipt) -> str:
    return " ".join(
        value
        for value in (
            receipt.keep_title,
            receipt.keep_proof,
            receipt.notice_title,
            receipt.notice_proof,
            receipt.try_text,
            receipt.try_reason,
            receipt.visible_check,
        )
        if value
    )


def _subject_iou(shot: Shot, analysis: Analysis, expected: tuple[float, ...]) -> float:
    cells = analysis.composition.subject_cells
    if not cells or shot.grid is None:
        return 0.0
    grid = Grid(
        cols=shot.grid.cols,
        rows=shot.grid.rows,
        width=shot.grid.width,
        height=shot.grid.height,
    )
    box = grid.span_bounds(cells)
    actual = (
        box.left / grid.width,
        box.top / grid.height,
        box.right / grid.width,
        box.bottom / grid.height,
    )
    left = max(actual[0], expected[0])
    top = max(actual[1], expected[1])
    right = min(actual[2], expected[2])
    bottom = min(actual[3], expected[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    actual_area = (actual[2] - actual[0]) * (actual[3] - actual[1])
    expected_area = (expected[2] - expected[0]) * (expected[3] - expected[1])
    union = actual_area + expected_area - intersection
    return intersection / union if union else 0.0


def evaluate(
    case: QualityCase,
    shot: Shot,
    analysis: Analysis,
    receipt: ShotTeachingReceipt,
) -> list[dict]:
    expected = case.expectations
    checks: list[dict] = []
    techniques = {item.technique_id for item in analysis.techniques}
    finding_ids = {item.finding_id for item in analysis.findings}
    visible = _visible_text(receipt)

    checks.append(
        _check(
            "taxonomy",
            techniques <= taxonomy.BY_ID.keys(),
            f"stored Technique ids: {sorted(techniques)}",
        )
    )
    checks.append(
        _check(
            "receipt has no internal cells",
            CELL_REF.search(visible) is None
            and GRID_JARGON.search(visible) is None
            and BARE_GRID_COLUMN.search(visible) is None,
            f"visible characters: {len(visible)}",
        )
    )
    checks.append(
        _check(
            "receipt has no clipped clause",
            all(
                DANGLING_CONNECTOR.search(value) is None
                and ORPHAN_LOCATOR.search(value) is None
                and ORPHAN_PREPOSITION_PAIR.search(value) is None
                and DANGLING_PARTICIPLE.search(value) is None
                for value in (
                    receipt.keep_proof,
                    receipt.notice_title,
                    receipt.try_text,
                    receipt.try_reason,
                    receipt.visible_check,
                )
            ),
            "visible receipt clauses are complete",
        )
    )
    checks.append(
        _check(
            "receipt is bounded",
            len(visible) <= expected.max_visible_characters,
            f"{len(visible)} <= {expected.max_visible_characters}",
        )
    )
    checks.append(
        _check(
            "authority labels",
            receipt.keep_authority in {None, "model_read"}
            and receipt.notice_authority in {None, "measured", "model_read"}
            and not (receipt.notice_authority == "measured" and not receipt.notice_finding_id),
            (
                f"keep={receipt.keep_authority or 'none'}, "
                f"notice={receipt.notice_authority or 'none'}"
            ),
        )
    )
    checks.append(
        _check(
            "one supported image layer",
            receipt.primary_layer in {"clean", "finding", "action", "guide"},
            receipt.primary_layer,
        )
    )
    protected = {receipt.keep_technique_id} if receipt.keep_technique_id else set()
    selected_move = next(
        (
            move
            for move in analysis.composition.moves
            if receipt.try_text.rstrip(".") == move.what.rstrip(".")
        ),
        None,
    )
    selected_conflicts = sorted(
        protected.intersection(selected_move.challenges_technique_ids)
        if selected_move is not None
        else set()
    )
    checks.append(
        _check(
            "Try preserves Keep",
            not selected_conflicts,
            f"selected Move challenges {selected_conflicts}",
        )
    )
    selected_warrant = selected_move.warrant.value if selected_move is not None else "none"
    checks.append(
        _check(
            "Try has corrective warrant",
            selected_warrant not in {"guide", "variation"},
            f"selected Move warrant: {selected_warrant}",
        )
    )
    checks.append(
        _check(
            "Try has a concrete reason",
            selected_move is None or bool(selected_move.reason.strip()),
            "no Try selected" if selected_move is None else selected_move.reason,
        )
    )
    checks.append(
        _check(
            "abstention policy",
            expected.allow_abstention or not analysis.abstained,
            analysis.abstained or "panel did not abstain",
        )
    )
    for index, group in enumerate(expected.required_any_techniques, start=1):
        found = sorted(techniques & set(group))
        checks.append(
            _check(
                f"required Technique group {index}",
                bool(found),
                f"expected any of {group}; found {found}",
            )
        )
    forbidden_techniques = sorted(techniques & set(expected.forbidden_techniques))
    checks.append(
        _check(
            "forbidden Techniques",
            not forbidden_techniques,
            f"found {forbidden_techniques}",
        )
    )
    missing_findings = sorted(set(expected.required_findings) - finding_ids)
    checks.append(
        _check(
            "required Findings",
            not missing_findings,
            f"missing {missing_findings}; found {sorted(finding_ids)}",
        )
    )
    forbidden_findings = sorted(finding_ids & set(expected.forbidden_findings))
    checks.append(
        _check(
            "forbidden Findings",
            not forbidden_findings,
            f"found {forbidden_findings}",
        )
    )
    if expected.require_action:
        checks.append(
            _check(
                "actionable receipt",
                bool(receipt.try_text and receipt.visible_check),
                f"try={bool(receipt.try_text)}, check={bool(receipt.visible_check)}",
            )
        )
    if expected.acceptable_move_kinds:
        allowed = {item.value for item in expected.acceptable_move_kinds}
        actual = receipt.try_kind.value if receipt.try_kind else "none"
        checks.append(
            _check("Move kind", actual in allowed, f"expected {sorted(allowed)}; found {actual}")
        )
    forbidden_kinds = {item.value for item in expected.forbidden_move_kinds}
    actual_kind = receipt.try_kind.value if receipt.try_kind else "none"
    checks.append(
        _check(
            "forbidden Move kinds",
            actual_kind not in forbidden_kinds,
            f"forbidden {sorted(forbidden_kinds)}; found {actual_kind}",
        )
    )
    move_copy = f"{receipt.try_text} {receipt.try_reason}".lower()
    forbidden_phrases = [
        phrase for phrase in expected.forbidden_move_phrases if phrase.lower() in move_copy
    ]
    checks.append(
        _check(
            "forbidden Move phrases",
            not forbidden_phrases,
            f"found {forbidden_phrases}",
        )
    )
    if expected.acceptable_primary_layers:
        checks.append(
            _check(
                "primary layer",
                receipt.primary_layer in expected.acceptable_primary_layers,
                f"expected {expected.acceptable_primary_layers}; found {receipt.primary_layer}",
            )
        )
    if expected.expected_subject_box is not None:
        overlap = _subject_iou(shot, analysis, expected.expected_subject_box)
        checks.append(
            _check(
                "subject localization",
                overlap >= expected.minimum_subject_iou,
                f"IoU {overlap:.3f} >= {expected.minimum_subject_iou:.3f}",
            )
        )
    checks.extend(
        _review(f"human review {index}", prompt)
        for index, prompt in enumerate(expected.human_review, 1)
    )
    return checks


def reproject(
    manifest_path: Path,
    source_report_path: Path,
    output_path: Path,
) -> dict:
    """Rebuild deterministic receipts and checks over one saved real-model report."""
    manifest = QualityManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    source_bytes = source_report_path.read_bytes()
    source = json.loads(source_bytes)
    if source.get("manifest_sha256") != manifest_sha:
        raise ValueError("source report and manifest digests differ")
    cases_by_id = {case.id: case for case in manifest.cases}
    results: list[dict] = []
    for item in source.get("cases", []):
        case_id = str(item.get("id", ""))
        case = cases_by_id.get(case_id)
        if case is None:
            raise ValueError(f"source report case is absent from manifest: {case_id}")
        if item.get("error") or not item.get("analysis") or not item.get("shot_evidence"):
            results.append(item)
            continue
        evidence = item["shot_evidence"]
        shot = Shot(
            id=f"quality_{case_id}",
            user_id=f"quality_{case_id}",
            filename=str(item.get("filename", "")),
            mime_type=str(evidence.get("mime_type", "")),
            kind=evidence.get("kind", "still"),
            exif=evidence.get("exif", {}),
            tone=evidence.get("tone", {}),
            motion=evidence.get("motion"),
            grid=evidence.get("grid"),
        )
        analysis = Analysis.model_validate(item["analysis"])
        receipt = shot_teaching.build(shot, analysis)
        results.append(
            {
                **item,
                "teaching": receipt.model_dump(mode="json"),
                "checks": evaluate(case, shot, analysis, receipt),
            }
        )

    statuses = [check["status"] for item in results for check in item["checks"]]
    report = {
        **source,
        "reprojected_at": datetime.now(tz=UTC).isoformat(),
        "source_report_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "summary": {
            "pass": statuses.count("pass"),
            "fail": statuses.count("fail"),
            "review": statuses.count("review"),
            "errored_cases": sum(bool(item.get("error")) for item in results),
        },
        "cases": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"reprojected report: {output_path.resolve()}")
    print(json.dumps(report["summary"], indent=2))
    return report


async def run(
    manifest_path: Path,
    output_path: Path,
    limit: int | None,
    case_ids: list[str] | None = None,
) -> dict:
    manifest = QualityManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.cases
    if case_ids:
        wanted = set(case_ids)
        known = {case.id for case in cases}
        unknown = sorted(wanted - known)
        if unknown:
            raise ValueError(f"unknown requested case ids: {unknown}")
        cases = [case for case in cases if case.id in wanted]
    if limit:
        cases = cases[:limit]
    asset_root = output_path.parent / f"{output_path.stem}-assets"
    results: list[dict] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.id}: reading {Path(case.path).name}", flush=True)
        try:
            shot, analysis, receipt, artifacts, digest, elapsed = await _read_case(
                manifest_path, case, asset_root
            )
            checks = evaluate(case, shot, analysis, receipt)
            failures = sum(item["status"] == "fail" for item in checks)
            print(
                f"  {'FAIL' if failures else 'PASS'} in {elapsed:.1f}s; "
                f"{len(analysis.techniques)} Techniques, {len(analysis.findings)} Findings, "
                f"{failures} failed checks",
                flush=True,
            )
            results.append(
                {
                    "id": case.id,
                    "note": case.note,
                    "filename": shot.filename,
                    "input_sha256": digest,
                    "elapsed_seconds": round(elapsed, 3),
                    "model": analysis.model,
                    "prompt_version": analysis.prompt_version,
                    "shot_evidence": {
                        "kind": shot.kind.value,
                        "mime_type": shot.mime_type,
                        "exif": shot.exif.model_dump(mode="json", exclude_none=True),
                        "tone": shot.tone.model_dump(mode="json", exclude_none=True),
                        "motion": (
                            shot.motion.model_dump(mode="json", exclude_none=True)
                            if shot.motion is not None
                            else None
                        ),
                        "grid": shot.grid.model_dump() if shot.grid else None,
                    },
                    "analysis": analysis.model_dump(mode="json"),
                    "teaching": receipt.model_dump(mode="json"),
                    "artifacts": artifacts,
                    "checks": checks,
                    "error": "",
                }
            )
        except Exception as error:  # noqa: BLE001 - one failed case must not erase the corpus
            print(f"  ERROR: {type(error).__name__}: {error}", flush=True)
            results.append(
                {
                    "id": case.id,
                    "note": case.note,
                    "filename": Path(case.path).name,
                    "input_sha256": "",
                    "elapsed_seconds": 0,
                    "model": settings.model_flash,
                    "prompt_version": "",
                    "shot_evidence": None,
                    "analysis": None,
                    "teaching": None,
                    "artifacts": {},
                    "checks": [
                        _check("pipeline completed", False, f"{type(error).__name__}: {error}")
                    ],
                    "error": f"{type(error).__name__}: {error}",
                }
            )

    statuses = [check["status"] for item in results for check in item["checks"]]
    report = {
        "quality_version": QUALITY_VERSION,
        "manifest": manifest.name,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "created_at": datetime.now(tz=UTC).isoformat(),
        "model": settings.model_flash,
        "provider": "vertex" if settings.use_vertex_ai else "ai_studio",
        "model_location": settings.vertex_location if settings.use_vertex_ai else "",
        "case_count": len(results),
        "summary": {
            "pass": statuses.count("pass"),
            "fail": statuses.count("fail"),
            "review": statuses.count("review"),
            "errored_cases": sum(bool(item["error"]) for item in results),
        },
        "cases": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"report: {output_path.resolve()}")
    print(json.dumps(report["summary"], indent=2))
    return report


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument(
        "--reproject-report",
        type=Path,
        help="reuse saved real-model Analysis and rerun only deterministic receipt checks",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    manifest_path = args.manifest.resolve()
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = (
        args.output.resolve()
        if args.output
        else DEFAULT_OUTPUT_ROOT / f"learning-quality-{stamp}.json"
    )
    if args.reproject_report:
        if args.limit or args.case_ids:
            raise ValueError("--reproject-report cannot be combined with --limit or --case")
        report = reproject(
            manifest_path,
            args.reproject_report.resolve(),
            output_path,
        )
    else:
        report = asyncio.run(run(manifest_path, output_path, args.limit, args.case_ids))
    return 1 if report["summary"]["fail"] else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
