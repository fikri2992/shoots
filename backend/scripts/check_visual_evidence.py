"""Render real-corpus Visual Evidence Artifacts without calling a model.

This is a quality check, not a synthetic collaborator test. It exercises the
same domain routing and OpenCV/Pillow renderer used by the Analyst service and
writes inspectable images plus a machine-readable report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from PIL import Image, ImageOps

from app.domain import taxonomy
from app.domain import visual_evidence as routing
from app.domain.entities import (
    GridSpec,
    Shot,
    ShotKind,
    ShotSource,
    TechniqueEvidence,
    VisualPath,
    VisualPathRole,
)
from app.domain.grid import Grid
from app.imaging import visual_evidence

CASES: tuple[tuple[str, str, str], ...] = (
    ("complementary", "online-inspiration/06-complementary-colors.jpg", "complementary"),
    ("warm-cool", "generated-intent/13-intent-color-market.png", "warm_cool"),
    ("silhouette", "online-inspiration/04-sunset-silhouette.jpg", "silhouette"),
    ("hard-light", "online-inspiration/08-window-shadow.jpg", "hard_light"),
    ("shallow-dof", "online-inspiration/09-flower-bokeh.jpg", "shallow_dof"),
    ("bokeh", "online-inspiration/09-flower-bokeh.jpg", "bokeh_balls"),
    ("noise", "online-inspiration/07-rainy-night-street.jpg", "high_iso_night"),
    ("edges", "generated-intent/13-intent-color-market.png", "leading_lines"),
    ("panning-direction", "generated-intent/12-intent-panning-cyclist.png", "panning"),
    ("face-window", "online-inspiration/03-window-portrait.jpg", "eye_contact_portrait"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("../docs/test-corpus"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../docs/test-corpus/results/visual-evidence"),
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    still = [item for item in taxonomy.TECHNIQUES if not item.video_only]
    plan_errors = [item.id for item in still if item.id not in routing.PLANS]
    results: list[dict[str, object]] = []
    for case_id, relative_path, technique_id in CASES:
        path = args.corpus / relative_path
        source_bytes = path.read_bytes()
        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
        grid = Grid.for_image(*image.size)
        shot = Shot(
            id=f"visual-{case_id}",
            user_id="visual-quality",
            kind=ShotKind.PHOTO,
            source=ShotSource.DRIVE,
            filename=path.name,
            mime_type="image/jpeg",
            grid=GridSpec(cols=grid.cols, rows=grid.rows, width=image.width, height=image.height),
        )
        evidence = TechniqueEvidence(
            technique_id=technique_id,
            confidence=0.9,
            cells=grid.all_refs(),
            paths=(
                [
                    VisualPath(
                        points=["D9", "D7", "D5"],
                        leads_to=["D4", "E4"],
                        role=VisualPathRole.EDGE,
                    ),
                    VisualPath(
                        points=["G9", "F7", "E5"],
                        leads_to=["D4", "E4"],
                        role=VisualPathRole.EDGE,
                    ),
                ]
                if technique_id == "leading_lines"
                else []
            ),
            agreement=2,
        )
        started = time.perf_counter()
        rendered = visual_evidence.render(
            image,
            shot,
            evidence,
            hashlib.sha256(source_bytes).hexdigest()[:24],
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        output_path = ""
        if rendered.image is not None:
            destination = args.output / f"{case_id}-{rendered.artifact.kind.value}.jpg"
            rendered.image.save(destination, format="JPEG", quality=90, optimize=True)
            output_path = str(destination)
        results.append(
            {
                "case": case_id,
                "technique": technique_id,
                "kind": rendered.artifact.kind.value,
                "authority": rendered.artifact.authority.value,
                "status": rendered.artifact.status.value,
                "verification": rendered.artifact.verification.value,
                "refinement_count": rendered.artifact.refinement_count,
                "metrics": rendered.artifact.metrics,
                "elapsed_ms": elapsed_ms,
                "output": output_path,
            }
        )

    report = {
        "renderer_version": visual_evidence.RENDERER_VERSION,
        "still_techniques": len(still),
        "mapped_techniques": len(routing.PLANS),
        "plan_errors": plan_errors,
        "cases": results,
    }
    report_path = args.output / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if plan_errors or any(not item["output"] for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
