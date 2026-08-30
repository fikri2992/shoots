"""Compare bounded Analyst prompt experiments on the market benchmark Shot.

The production prompts remain untouched. Each experiment appends one explicit
evaluation question to the accountable lens, runs the real Ingest and Analyst
path, and preserves the complete Analysis, teaching receipt, and rendered
Visual Evidence Artifacts for inspection.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.agents import prompts
from scripts import check_learning_quality as quality

CASE_ID = "generated-color-market"
REPO_ROOT = Path(__file__).resolve().parents[2]

EXPERIMENTS: tuple[tuple[str, str, dict[str, str]], ...] = (
    (
        "geometry-accountability",
        "Can the panel trace the corridor rather than substitute a box?",
        {
            "composer": (
                "\n\nBENCHMARK QUESTION: GEOMETRY ACCOUNTABILITY\n"
                "Audit every path-shaped composition claim without assuming that a path exists. "
                "For leading lines or diagonals, return each visible boundary as its own ordered "
                "Visual Path from near origin toward a named target. If only a broad corridor can "
                "be located, omit the path-shaped Technique instead of fitting a line through "
                "cells."
            )
        },
    ),
    (
        "colour-alternatives",
        "Does the colour read distinguish accent, complementary, and warm/cool?",
        {
            "storyteller": (
                "\n\nBENCHMARK QUESTION: COLOUR ALTERNATIVES\n"
                "Audit the visible colour relationship without assuming its name. Explicitly "
                "distinguish a single accent from complementary hues and from a warm/cool "
                "temperature relationship. Choose only what the frame supports, attach separate "
                "Visual Regions to every claimed member, and omit a relationship when its second "
                "member cannot be located confidently."
            )
        },
    ),
    (
        "depth-members",
        "Can the panel keep foreground, subject corridor, and background separate?",
        {
            "composer": (
                "\n\nBENCHMARK QUESTION: DEPTH MEMBERS\n"
                "Audit depth without assuming layering. Name layering or deep depth only when "
                "foreground, midground, and background can be located separately. Return those "
                "members as ordered Visual Regions and never flatten them into one cell cloud."
            )
        },
    ),
    (
        "teaching-restraint",
        "Can the lesson preserve what works and offer one checkable next capture?",
        {
            "composer": (
                "\n\nBENCHMARK QUESTION: TEACHING RESTRAINT\n"
                "After the read, propose at most one next-capture Move. It must preserve the "
                "strongest supported Technique, name one visible tension, and state what should "
                "look different afterward. Leave Moves empty when no warranted change clearly wins."
            ),
            "synthesizer": (
                "\n\nBENCHMARK QUESTION: TEACHING RESTRAINT\n"
                "Order the critique as: strongest supported decision, its visible effect, one "
                "remaining tension, and one checkable next-capture result. Do not grade, infer "
                "Intent, or expose grid-cell names."
            ),
        },
    ),
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("../docs/test-corpus/learning-quality.json"),
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("../docs/test-corpus/results/visual-evidence-real-model.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("../docs/test-corpus/results/market-story-experiments"),
    )
    return parser.parse_args()


def _case(report: dict) -> dict:
    return next(item for item in report["cases"] if item["id"] == CASE_ID)


def _summary(case: dict) -> dict:
    analysis = case.get("analysis") or {}
    teaching = case.get("teaching") or {}
    techniques = analysis.get("techniques") or []
    return {
        "elapsed_seconds": case.get("elapsed_seconds", 0),
        "techniques": [
            {
                "technique_id": item.get("technique_id", ""),
                "confidence": item.get("confidence", 0),
                "agreement": item.get("agreement", 0),
                "path_count": len(item.get("paths") or []),
                "region_count": len(item.get("regions") or []),
                "artifact": (item.get("visual_artifact") or {}).get("kind", ""),
            }
            for item in techniques
        ],
        "guide": (analysis.get("composition") or {}).get("guide", ""),
        "keep_title": teaching.get("keep_title", ""),
        "try_text": teaching.get("try_text", ""),
        "visible_check": teaching.get("visible_check", ""),
        "failed_checks": [
            item.get("name", "") for item in case.get("checks", []) if item.get("status") == "fail"
        ],
    }


def _portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def _portable_report(value: object) -> object:
    if isinstance(value, dict):
        return {key: _portable_report(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_portable_report(item) for item in value]
    if isinstance(value, str):
        path = Path(value)
        if path.is_absolute():
            return _portable_path(path)
    return value


def _variant_loader(
    base: Callable[[str], str],
    additions: dict[str, str],
) -> Callable[[str], str]:
    def load(name: str) -> str:
        return base(name) + additions.get(name, "")

    return load


def _artifact_path(case: dict, asset_root: Path, preferred: tuple[str, ...]) -> Path | None:
    techniques = (case.get("analysis") or {}).get("techniques") or []
    by_id = {item.get("technique_id"): item for item in techniques}
    for technique_id in preferred:
        artifact = (by_id.get(technique_id) or {}).get("visual_artifact") or {}
        blob_path = artifact.get("blob_path", "")
        candidate = asset_root / blob_path
        if artifact.get("status") == "rendered" and blob_path and candidate.is_file():
            return candidate
    annotated = Path((case.get("artifacts") or {}).get("annotated", ""))
    return annotated if annotated.is_file() else None


def _write_preview(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        ImageOps.exif_transpose(image).convert("RGB").save(destination, quality=90)


def _contact_sheet(items: list[tuple[str, str, Path, dict]], output: Path) -> None:
    panel_width, image_height, text_height = 520, 650, 190
    panel_height = image_height + text_height
    columns = 2
    rows = (len(items) + columns - 1) // columns
    sheet = Image.new("RGB", (panel_width * columns, panel_height * rows), "#0b0b0c")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (name, question, path, summary) in enumerate(items):
        x = (index % columns) * panel_width
        y = (index // columns) * panel_height
        with Image.open(path) as raw:
            image = ImageOps.contain(
                ImageOps.exif_transpose(raw).convert("RGB"), (panel_width, image_height)
            )
        image_x = x + (panel_width - image.width) // 2
        sheet.paste(image, (image_x, y))
        technique_line = ", ".join(
            f"{item['technique_id']} a{item['agreement']} "
            f"p{item['path_count']} r{item['region_count']}"
            for item in summary["techniques"][:5]
        )
        lines = [
            name,
            question,
            f"Guide: {summary['guide']} | Keep: {summary['keep_title']}",
            technique_line,
            f"Try: {summary['try_text'] or 'none'}",
        ]
        text_y = y + image_height + 12
        for line in lines:
            draw.text((x + 12, text_y), line[:82], fill="#f4efe6", font=font)
            text_y += 28
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=88)


async def run(manifest: Path, baseline_path: Path, output_dir: Path) -> dict:
    manifest = manifest.resolve()
    baseline_path = baseline_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline_report = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_case = _case(baseline_report)
    baseline_assets = baseline_path.parent / f"{baseline_path.stem}-assets"
    collected: list[dict] = [
        {
            "id": "production-baseline",
            "question": "What does the current production panel say without extra prompting?",
            "prompt_addition_sha256": "",
            "report": str(baseline_path),
            "asset_root": str(baseline_assets),
            "case": baseline_case,
            "summary": _summary(baseline_case),
        }
    ]

    base_load = prompts.load
    try:
        for index, (name, question, additions) in enumerate(EXPERIMENTS, start=1):
            print(f"[{index}/{len(EXPERIMENTS)}] {name}", flush=True)
            prompts.load = _variant_loader(base_load, additions)
            prompts.version.cache_clear()
            prompts.bundle_version.cache_clear()
            report_path = output_dir / f"{name}.json"
            report = await quality.run(manifest, report_path, None, [CASE_ID])
            case = _case(report)
            report_path.write_text(
                json.dumps(_portable_report(report), indent=2),
                encoding="utf-8",
            )
            addition_source = "\n".join(
                f"{key}\n{value}" for key, value in sorted(additions.items())
            )
            collected.append(
                {
                    "id": name,
                    "question": question,
                    "prompt_addition_sha256": hashlib.sha256(addition_source.encode()).hexdigest(),
                    "report": str(report_path),
                    "asset_root": str(report_path.parent / f"{report_path.stem}-assets"),
                    "case": case,
                    "summary": _summary(case),
                }
            )
    finally:
        prompts.load = base_load
        prompts.version.cache_clear()
        prompts.bundle_version.cache_clear()

    preferred = {
        "production-baseline": ("single_accent", "leading_lines", "layering"),
        "geometry-accountability": ("leading_lines", "diagonals", "frame_within_frame"),
        "colour-alternatives": ("complementary", "warm_cool", "single_accent"),
        "depth-members": ("layering", "deep_dof", "leading_lines"),
        "teaching-restraint": ("leading_lines", "single_accent", "layering"),
    }
    previews: list[tuple[str, str, Path, dict]] = []
    for item in collected:
        source = _artifact_path(
            item["case"],
            Path(item["asset_root"]),
            preferred[item["id"]],
        )
        if source is None:
            continue
        preview = output_dir / f"{item['id']}.jpg"
        _write_preview(source, preview)
        item["preview"] = str(preview)
        previews.append((item["id"], item["question"], preview, item["summary"]))

    contact_sheet = output_dir / "comparison.jpg"
    _contact_sheet(previews, contact_sheet)
    aggregate = {
        "created_at": datetime.now(tz=UTC).isoformat(),
        "case_id": CASE_ID,
        "input_sha256": baseline_case.get("input_sha256", ""),
        "experiments": [
            {
                key: (
                    _portable_path(Path(value))
                    if key in {"report", "asset_root", "preview"}
                    else value
                )
                for key, value in item.items()
                if key != "case"
            }
            for item in collected
        ],
        "contact_sheet": _portable_path(contact_sheet),
    }
    aggregate_path = output_dir / "summary.json"
    aggregate_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    print(f"summary: {aggregate_path}")
    print(f"comparison: {contact_sheet}")
    return aggregate


def main() -> int:
    args = _arguments()
    asyncio.run(run(args.manifest, args.baseline, args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
