"""Render inspectable pixel support for still-Technique Evidence.

Gemini supplies Technique ids and bounded grid cells. This module alone turns
pixels into maps. A rendered map is deliberately narrower than the Technique
claim: it says, for example, where local contrast is high, not that shallow
depth of field was intentional or successful.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from app.domain import visual_evidence as routing
from app.domain.entities import (
    Shot,
    TechniqueEvidence,
    VisualArtifactAuthority,
    VisualArtifactKind,
    VisualArtifactStatus,
    VisualArtifactVerification,
    VisualEvidenceArtifact,
)
from app.domain.grid import Grid, GridError

RENDERER_VERSION = "visual-evidence-v2"
MAX_EDGE = 1280
EVIDENCE_CYAN = np.array([54, 196, 220], dtype=np.float32)
EVIDENCE_VIOLET = np.array([203, 126, 235], dtype=np.float32)
YUNET_MODEL = Path(__file__).resolve().parent / "models" / "face_detection_yunet_2026may.onnx"


@dataclass(frozen=True)
class RenderedVisualEvidence:
    artifact: VisualEvidenceArtifact
    image: Image.Image | None = None


def render(
    image: Image.Image,
    shot: Shot,
    evidence: TechniqueEvidence,
    source_digest: str,
) -> RenderedVisualEvidence:
    """Render the first supported pixel strategy, or a typed honest fallback."""
    frame = _fit(image.convert("RGB"))
    rgb = np.asarray(frame, dtype=np.uint8)
    source = _source_mask(frame.size, shot, evidence.cells)
    plan = routing.plan_for(evidence.technique_id)
    candidates = (plan.primary, *plan.supporting)

    for strategy in candidates:
        rendered = _try_strategy(strategy, rgb, source, shot, evidence)
        if rendered is None:
            continue
        artifact, pixels = rendered
        artifact.source_digest = source_digest
        artifact.renderer_version = RENDERER_VERSION
        artifact.metrics.update(_exif_metrics(shot))
        return RenderedVisualEvidence(artifact=artifact, image=Image.fromarray(pixels, "RGB"))

    if routing.VisualStrategyKind.EXIF in candidates:
        metrics = _exif_metrics(shot)
        if metrics:
            return RenderedVisualEvidence(
                VisualEvidenceArtifact(
                    kind=VisualArtifactKind.EXIF_RECEIPT,
                    authority=VisualArtifactAuthority.MEASURED,
                    status=VisualArtifactStatus.RENDERED,
                    verification=VisualArtifactVerification.MEASURED,
                    label="Camera receipt",
                    legend="Recorded by the camera; it does not grade the result.",
                    metrics=metrics,
                    source_digest=source_digest,
                    renderer_version=RENDERER_VERSION,
                )
            )

    geometry_present = bool(evidence.cells or evidence.paths)
    return RenderedVisualEvidence(
        VisualEvidenceArtifact(
            kind=VisualArtifactKind.GEOMETRY,
            authority=(
                VisualArtifactAuthority.LOCATED_MODEL_READ
                if geometry_present
                else VisualArtifactAuthority.UNRESOLVED
            ),
            status=(
                VisualArtifactStatus.FALLBACK
                if geometry_present
                else VisualArtifactStatus.UNRESOLVED
            ),
            verification=(
                VisualArtifactVerification.FALLBACK
                if geometry_present
                else VisualArtifactVerification.REJECTED
            ),
            label="Located model read" if geometry_present else "Visual location unresolved",
            legend=(
                "Broad Analyst cells; no precise pixel detector supported this claim."
                if geometry_present
                else "Shoots could not honestly point to this claim in the frame."
            ),
            source_digest=source_digest,
            renderer_version=RENDERER_VERSION,
            fallback_reason=f"No supported renderer for {plan.primary.value}",
        )
    )


def _try_strategy(
    strategy: routing.VisualStrategyKind,
    rgb: np.ndarray,
    source: np.ndarray,
    shot: Shot,
    evidence: TechniqueEvidence,
) -> tuple[VisualEvidenceArtifact, np.ndarray] | None:
    technique_id = evidence.technique_id
    if strategy is routing.VisualStrategyKind.PATHS:
        return _verified_paths(rgb, shot, evidence)
    if strategy is routing.VisualStrategyKind.REGION:
        return _subject_contour(rgb, source, technique_id)
    if strategy is routing.VisualStrategyKind.HUE:
        return _hue(rgb, source, technique_id)
    if strategy is routing.VisualStrategyKind.SATURATION:
        return _saturation(rgb, source)
    if strategy is routing.VisualStrategyKind.LUMINANCE:
        return _luminance(rgb, source, technique_id)
    if strategy is routing.VisualStrategyKind.SHARPNESS:
        return _sharpness(rgb, source)
    if strategy is routing.VisualStrategyKind.NOISE:
        return _noise(rgb, source)
    if strategy is routing.VisualStrategyKind.EDGES:
        if technique_id in {"leading_lines", "diagonals", "light_trails", "light_painting"}:
            return None
        return _edges(rgb, source)
    if strategy is routing.VisualStrategyKind.BOKEH:
        return _bokeh(rgb, source)
    if strategy is routing.VisualStrategyKind.BLUR_DIRECTION:
        return _blur_direction(rgb, source, evidence, shot)
    if strategy is routing.VisualStrategyKind.RADIAL_BLUR:
        return _radial_blur(rgb, source)
    if strategy is routing.VisualStrategyKind.FACE_LANDMARKS:
        return _face_landmarks(rgb, source, technique_id)
    return None


def _fit(image: Image.Image) -> Image.Image:
    longest = max(image.size)
    if longest <= MAX_EDGE:
        return image
    scale = MAX_EDGE / longest
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )


def _source_mask(size: tuple[int, int], shot: Shot, cells: list[str]) -> np.ndarray:
    width, height = size
    mask = np.zeros((height, width), dtype=bool)
    if not cells or shot.grid is None:
        mask[:] = True
        return mask
    grid = Grid(cols=shot.grid.cols, rows=shot.grid.rows, width=width, height=height)
    valid = 0
    for ref in cells:
        try:
            box = grid.cell_bounds(ref)
        except GridError:
            continue
        mask[box.top : box.bottom, box.left : box.right] = True
        valid += 1
    if not valid:
        mask[:] = True
    return mask


def _artifact(
    kind: VisualArtifactKind,
    label: str,
    legend: str,
    metrics: dict[str, float | int | str],
) -> VisualEvidenceArtifact:
    return VisualEvidenceArtifact(
        kind=kind,
        authority=VisualArtifactAuthority.MEASURED,
        verification=VisualArtifactVerification.MEASURED,
        label=label,
        legend=legend,
        metrics=metrics,
        renderer_version=RENDERER_VERSION,
    )


def _hue(
    rgb: np.ndarray, source: np.ndarray, technique_id: str
) -> tuple[VisualEvidenceArtifact, np.ndarray] | None:
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[..., 0].astype(np.float32) * 2.0
    saturation = hsv[..., 1].astype(np.float32) / 255.0
    value = hsv[..., 2].astype(np.float32) / 255.0
    coloured = source & (saturation >= 0.18) & (value >= 0.12)
    if not np.any(coloured):
        return None

    if technique_id == "warm_cool":
        first = coloured & ((hue < 75) | (hue >= 330))
        second = coloured & (hue >= 150) & (hue < 285)
        names = ("warm", "cool")
    elif technique_id == "golden_hour":
        first = coloured & ((hue < 70) | (hue >= 345))
        second = np.zeros_like(first)
        names = ("warm", "")
    elif technique_id == "blue_hour":
        first = coloured & (hue >= 180) & (hue < 270)
        second = np.zeros_like(first)
        names = ("blue", "")
    elif technique_id == "single_accent":
        first = source & (saturation >= 0.58) & (value >= 0.18)
        second = np.zeros_like(first)
        names = ("saturated accent", "")
    else:
        sectors = np.floor(hue[coloured] / 30).astype(np.int32) % 12
        counts = np.bincount(sectors, minlength=12)
        ranked = np.argsort(counts)[::-1]
        first_sector = int(ranked[0])
        second_sector = next(
            (
                int(candidate)
                for candidate in ranked[1:]
                if counts[candidate] > 0
                and min(abs(int(candidate) - first_sector), 12 - abs(int(candidate) - first_sector))
                >= 3
            ),
            int(ranked[1]) if len(ranked) > 1 else first_sector,
        )
        first = coloured & ((np.floor(hue / 30).astype(np.int32) % 12) == first_sector)
        second = coloured & ((np.floor(hue / 30).astype(np.int32) % 12) == second_sector)
        names = (f"hue {first_sector * 30}°", f"hue {second_sector * 30}°")

    first = _clean_mask(first, max_components=28)
    second = _clean_mask(second, max_components=28)
    if not np.any(first) and not np.any(second):
        return None
    pixels = _two_mask_overlay(rgb, first, second)
    total = max(1, int(np.count_nonzero(source)))
    metrics: dict[str, float | int | str] = {
        "primary_share_pct": round(100 * int(np.count_nonzero(first)) / total, 1),
        "primary_group": names[0],
    }
    if np.any(second):
        metrics["secondary_share_pct"] = round(100 * int(np.count_nonzero(second)) / total, 1)
        metrics["secondary_group"] = names[1]
    return (
        _artifact(
            VisualArtifactKind.HUE_MASK,
            "Where the colour lives",
            "Cyan and violet mark measured hue groups; unmarked pixels did not meet the hue mask.",
            metrics,
        ),
        pixels,
    )


def _saturation(rgb: np.ndarray, source: np.ndarray) -> tuple[VisualEvidenceArtifact, np.ndarray]:
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    saturation = hsv[..., 1]
    pixels = _heat_overlay(rgb, saturation, source)
    values = saturation[source].astype(np.float32) / 255.0 * 100
    return (
        _artifact(
            VisualArtifactKind.SATURATION_MAP,
            "Saturation across the frame",
            "Blue is lower saturation; yellow is higher saturation.",
            {
                "mean_saturation_pct": round(float(np.mean(values)), 1),
                "p95_saturation_pct": round(float(np.percentile(values, 95)), 1),
            },
        ),
        pixels,
    )


def _luminance(
    rgb: np.ndarray, source: np.ndarray, technique_id: str
) -> tuple[VisualEvidenceArtifact, np.ndarray]:
    luma = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    pixels = _heat_overlay(rgb, luma, source)
    values = luma[source].astype(np.float32)
    return (
        _artifact(
            VisualArtifactKind.LUMINANCE_MAP,
            "Light across the frame",
            "Blue is darker; yellow is brighter. This maps luminance, not the light source.",
            {
                "mean_luma": round(float(np.mean(values)), 1),
                "p05_luma": round(float(np.percentile(values, 5)), 1),
                "p95_luma": round(float(np.percentile(values, 95)), 1),
                "dark_share_pct": round(float(np.mean(values <= 32) * 100), 1),
                "bright_share_pct": round(float(np.mean(values >= 224) * 100), 1),
                "technique_context": technique_id,
            },
        ),
        pixels,
    )


def _sharpness(rgb: np.ndarray, source: np.ndarray) -> tuple[VisualEvidenceArtifact, np.ndarray]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    laplacian = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    local = cv2.GaussianBlur(laplacian, (0, 0), sigmaX=5)
    scale = max(1.0, float(np.percentile(local[source], 98)))
    normalized = np.clip(local / scale * 255.0, 0, 255).astype(np.uint8)
    pixels = _heat_overlay(rgb, normalized, source, sparse=True)
    inside = local[source]
    outside = local[~source]
    metrics: dict[str, float | int | str] = {
        "median_local_contrast": round(float(np.median(inside)), 2),
        "p90_local_contrast": round(float(np.percentile(inside, 90)), 2),
    }
    if outside.size:
        metrics["outside_median_local_contrast"] = round(float(np.median(outside)), 2)
    return (
        _artifact(
            VisualArtifactKind.SHARPNESS_MAP,
            "Where detail stays sharp",
            "Blue is lower local contrast; yellow is higher. "
            "This is a sharpness proxy, not a depth sensor.",
            metrics,
        ),
        pixels,
    )


def _noise(rgb: np.ndarray, source: np.ndarray) -> tuple[VisualEvidenceArtifact, np.ndarray]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    smooth = cv2.medianBlur(gray, 5)
    residual = cv2.absdiff(gray, smooth)
    gradient = cv2.magnitude(
        cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3),
        cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3),
    )
    flat_limit = float(np.percentile(gradient[source], 55))
    flat = source & (gradient <= flat_limit)
    measured = residual[flat] if np.any(flat) else residual[source]
    scale = max(1.0, float(np.percentile(measured, 99)))
    normalized = np.zeros_like(residual)
    normalized[flat] = np.clip(
        residual[flat].astype(np.float32) / scale * 255.0,
        0,
        255,
    ).astype(np.uint8)
    pixels = _heat_overlay(rgb, normalized, source, sparse=True)
    values = measured.astype(np.float32)
    return (
        _artifact(
            VisualArtifactKind.NOISE_MAP,
            "Fine variation across the frame",
            "Warmer marks show stronger residual inside flatter areas. This suppresses "
            "most object edges but still supports rather than proves noise.",
            {
                "median_residual": round(float(np.median(values)), 2),
                "p95_residual": round(float(np.percentile(values, 95)), 2),
            },
        ),
        pixels,
    )


def _edges(rgb: np.ndarray, source: np.ndarray) -> tuple[VisualEvidenceArtifact, np.ndarray] | None:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 60, 150).astype(bool) & source
    if np.count_nonzero(edges) < 10:
        return None
    pixels = _mask_overlay(rgb, edges, EVIDENCE_CYAN, alpha=0.82, dim=0.82)
    return (
        _artifact(
            VisualArtifactKind.EDGE_MAP,
            "Visible edges in the named area",
            "Cyan marks measured contrast edges. It does not choose which edge carries "
            "the composition.",
            {"edge_share_pct": round(float(np.mean(edges[source]) * 100), 2)},
        ),
        pixels,
    )


def _verified_paths(
    rgb: np.ndarray,
    shot: Shot,
    evidence: TechniqueEvidence,
) -> tuple[VisualEvidenceArtifact, np.ndarray] | None:
    if shot.grid is None or not evidence.paths:
        return None
    height, width = rgb.shape[:2]
    grid = Grid(cols=shot.grid.cols, rows=shot.grid.rows, width=width, height=height)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gradient = cv2.magnitude(
        cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3),
        cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3),
    )
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 55, 140)
    search_radius = max(5, round(min(width / grid.cols, height / grid.rows) * 0.42))
    accepted: list[tuple[list[tuple[int, int]], list[tuple[int, int]], float]] = []
    for visual_path in evidence.paths[:3]:
        raw_points: list[tuple[int, int]] = []
        for ref in visual_path.points:
            try:
                raw_points.append(grid.cell_bounds(ref).center)
            except GridError:
                continue
        if len(raw_points) < 2:
            continue
        snapped = [_snap_point(point, edges, gradient, search_radius) for point in raw_points]
        line_mask = np.zeros_like(edges)
        cv2.polylines(line_mask, [np.asarray(snapped, dtype=np.int32)], False, 255, 2)
        tolerance = max(3, round(search_radius * 0.32))
        supported_edges = cv2.dilate(edges, np.ones((tolerance, tolerance), np.uint8)) > 0
        path_pixels = line_mask > 0
        support = float(np.mean(supported_edges[path_pixels])) if np.any(path_pixels) else 0.0
        if support < 0.42:
            continue
        targets: list[tuple[int, int]] = []
        if visual_path.leads_to:
            with suppress(GridError):
                targets.append(grid.span_bounds(visual_path.leads_to).center)
        if evidence.technique_id == "leading_lines" and not targets:
            continue
        accepted.append((snapped, targets, support))
    if not accepted:
        return None

    out = Image.fromarray(rgb.copy(), "RGB")
    draw = ImageDraw.Draw(out, "RGBA")
    stroke = max(3, round(min(width, height) / 260))
    for points, targets, _ in accepted:
        for target in targets:
            draw.line(
                (points[-1], target),
                fill=(0, 0, 0, 150),
                width=max(2, stroke * 2),
            )
            draw.line(
                (points[-1], target),
                fill=(245, 240, 231, 210),
                width=max(1, stroke // 2),
            )
        draw.line(points, fill=(0, 0, 0, 170), width=stroke * 3, joint="curve")
        draw.line(points, fill=(54, 196, 220, 245), width=stroke, joint="curve")
        radius = stroke * 2
        for x, y in (points[0], points[-1]):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(54, 196, 220, 240))
        for x, y in targets:
            ring = stroke * 4
            draw.ellipse(
                (x - ring, y - ring, x + ring, y + ring),
                outline=(54, 196, 220, 235),
                width=stroke,
            )
    supports = [item[2] for item in accepted]
    return (
        VisualEvidenceArtifact(
            kind=VisualArtifactKind.VERIFIED_PATHS,
            authority=VisualArtifactAuthority.LOCATED_MODEL_READ,
            status=VisualArtifactStatus.RENDERED,
            verification=VisualArtifactVerification.BOUNDED,
            refinement_count=1,
            label="Visible paths supporting the composition",
            legend=(
                "Cyan follows contrast edges inside the Analyst's bounded path corridors; "
                "separate paths remain separate, and the pale connector points to the target."
            ),
            metrics={
                "path_count": len(accepted),
                "mean_edge_support_pct": round(float(np.mean(supports)) * 100, 1),
            },
            renderer_version=RENDERER_VERSION,
        ),
        np.asarray(out, dtype=np.uint8),
    )


def _snap_point(
    point: tuple[int, int],
    edges: np.ndarray,
    gradient: np.ndarray,
    radius: int,
) -> tuple[int, int]:
    x, y = point
    height, width = edges.shape
    x0, x1 = max(0, x - radius), min(width, x + radius + 1)
    y0, y1 = max(0, y - radius), min(height, y + radius + 1)
    candidates = np.argwhere(edges[y0:y1, x0:x1] > 0)
    if not candidates.size:
        return point
    ys = candidates[:, 0] + y0
    xs = candidates[:, 1] + x0
    distance = np.hypot(xs - x, ys - y)
    strength = gradient[ys, xs]
    score = distance / max(1, radius) - strength / max(1.0, float(np.max(strength))) * 0.35
    index = int(np.argmin(score))
    return int(xs[index]), int(ys[index])


def _subject_contour(
    rgb: np.ndarray,
    source: np.ndarray,
    technique_id: str,
) -> tuple[VisualEvidenceArtifact, np.ndarray] | None:
    supported = {"fill_the_frame", "negative_space", "minimalism", "macro"}
    if technique_id not in supported or np.all(source):
        return None
    ys, xs = np.where(source)
    if not xs.size:
        return None
    height, width = source.shape
    left, right = int(xs.min()), int(xs.max()) + 1
    top, bottom = int(ys.min()), int(ys.max()) + 1
    if right - left < 12 or bottom - top < 12:
        return None
    rect = (
        max(1, left),
        max(1, top),
        min(width - 2, right) - max(1, left),
        min(height - 2, bottom) - max(1, top),
    )
    if rect[2] < 10 or rect[3] < 10:
        return None
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    mask = np.zeros((height, width), np.uint8)
    background = np.zeros((1, 65), np.float64)
    foreground = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, mask, rect, background, foreground, 4, cv2.GC_INIT_WITH_RECT)
    candidate = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, connectivity=8)
    if count <= 1:
        return None
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    subject = labels == largest
    subject_area = int(np.count_nonzero(subject))
    source_area = int(np.count_nonzero(source))
    if subject_area < max(64, source_area * 0.04) or subject_area > source_area * 0.94:
        return None
    contours, _ = cv2.findContours(
        subject.astype(np.uint8) * 255,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    if not contours:
        return None
    out = rgb.copy()
    cv2.drawContours(
        out,
        contours,
        -1,
        color=(54, 196, 220),
        thickness=max(2, round(min(width, height) / 350)),
        lineType=cv2.LINE_AA,
    )
    overlay = out.astype(np.float32)
    overlay[subject] = overlay[subject] * 0.82 + EVIDENCE_CYAN * 0.18
    return (
        VisualEvidenceArtifact(
            kind=VisualArtifactKind.SUBJECT_CONTOUR,
            authority=VisualArtifactAuthority.LOCATED_MODEL_READ,
            status=VisualArtifactStatus.RENDERED,
            verification=VisualArtifactVerification.BOUNDED,
            refinement_count=1,
            label="Subject extent inside the located area",
            legend=(
                "Cyan refines the Analyst's subject cells with a bounded foreground cut; "
                "it is not a semantic ground-truth mask."
            ),
            metrics={
                "frame_occupancy_pct": round(subject_area / (width * height) * 100, 1),
                "located_area_occupancy_pct": round(subject_area / source_area * 100, 1),
            },
            renderer_version=RENDERER_VERSION,
        ),
        np.clip(overlay, 0, 255).astype(np.uint8),
    )


def _blur_direction(
    rgb: np.ndarray,
    source: np.ndarray,
    evidence: TechniqueEvidence,
    shot: Shot,
) -> tuple[VisualEvidenceArtifact, np.ndarray] | None:
    region_cells = [
        cell
        for region in evidence.regions
        if region.role.value == "blurred"
        for cell in region.cells
    ]
    if region_cells:
        source = _source_mask((rgb.shape[1], rgb.shape[0]), shot, region_cells)
        region_note = "blurred member"
    else:
        region_note = "located area"
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(gx, gy)
    threshold = float(np.percentile(magnitude[source], 70))
    sample = source & (magnitude >= max(6.0, threshold))
    if np.count_nonzero(sample) < 120:
        return None
    # Edge gradients are perpendicular to the visible streak direction.
    direction = np.arctan2(gy[sample], gx[sample]) + np.pi / 2
    weights = magnitude[sample]
    cosine = float(np.average(np.cos(2 * direction), weights=weights))
    sine = float(np.average(np.sin(2 * direction), weights=weights))
    coherence = float(np.hypot(cosine, sine))
    if coherence < 0.24:
        return None
    angle = 0.5 * float(np.arctan2(sine, cosine))
    height, width = gray.shape
    ys, xs = np.where(source)
    left, right = int(xs.min()), int(xs.max())
    top, bottom = int(ys.min()), int(ys.max())
    spacing = max(35, round(min(width, height) / 8))
    length = spacing * 0.72
    dx = float(np.cos(angle) * length / 2)
    dy = float(np.sin(angle) * length / 2)
    out = Image.fromarray(rgb.copy(), "RGB")
    draw = ImageDraw.Draw(out, "RGBA")
    stroke = max(2, round(min(width, height) / 420))
    drawn = 0
    for y in range(top + spacing // 2, bottom + 1, spacing):
        for x in range(left + spacing // 2, right + 1, spacing):
            if not source[y, x]:
                continue
            start = (round(x - dx), round(y - dy))
            end = (round(x + dx), round(y + dy))
            draw.line((start, end), fill=(0, 0, 0, 160), width=stroke * 3)
            draw.line((start, end), fill=(54, 196, 220, 235), width=stroke)
            drawn += 1
    if not drawn:
        return None
    angle_deg = (float(np.degrees(angle)) + 180) % 180
    return (
        VisualEvidenceArtifact(
            kind=VisualArtifactKind.BLUR_DIRECTION,
            authority=VisualArtifactAuthority.LOCATED_MODEL_READ,
            status=VisualArtifactStatus.RENDERED,
            verification=VisualArtifactVerification.BOUNDED,
            label="Dominant directional structure",
            legend=(
                f"Cyan strokes show the dominant orientation measured in the {region_note}. "
                "It supports a blur reading but does not prove motion or Intent."
            ),
            metrics={
                "orientation_deg_from_horizontal": round(angle_deg, 1),
                "orientation_coherence_pct": round(coherence * 100, 1),
            },
            renderer_version=RENDERER_VERSION,
        ),
        np.asarray(out, dtype=np.uint8),
    )


def _radial_blur(
    rgb: np.ndarray,
    source: np.ndarray,
) -> tuple[VisualEvidenceArtifact, np.ndarray] | None:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 45, 125)
    edges[~source] = 0
    short = min(gray.shape)
    raw = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=max(25, short // 20),
        minLineLength=max(20, short // 9),
        maxLineGap=max(8, short // 45),
    )
    if raw is None or len(raw) < 6:
        return None
    equations: list[tuple[float, float, float]] = []
    segments: list[tuple[float, float, float, float]] = []
    for x1, y1, x2, y2 in np.asarray(raw).reshape(-1, 4)[:80]:
        dx, dy = float(x2 - x1), float(y2 - y1)
        length = float(np.hypot(dx, dy))
        if length < 1:
            continue
        nx, ny = -dy / length, dx / length
        equations.append((nx, ny, nx * x1 + ny * y1))
        segments.append((float(x1), float(y1), float(x2), float(y2)))
    if len(equations) < 6:
        return None
    matrix = np.asarray([[nx, ny] for nx, ny, _ in equations], dtype=np.float64)
    values = np.asarray([value for _, _, value in equations], dtype=np.float64)
    centre, _, _, _ = np.linalg.lstsq(matrix, values, rcond=None)
    cx, cy = float(centre[0]), float(centre[1])
    height, width = gray.shape
    if not (-0.25 * width <= cx <= 1.25 * width and -0.25 * height <= cy <= 1.25 * height):
        return None
    accepted: list[tuple[tuple[int, int], tuple[int, int], float]] = []
    for x1, y1, x2, y2 in segments:
        dx, dy = x2 - x1, y2 - y1
        line_length = float(np.hypot(dx, dy))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        rx, ry = mx - cx, my - cy
        radial_length = float(np.hypot(rx, ry))
        if line_length < 1 or radial_length < 1:
            continue
        alignment = abs((dx * rx + dy * ry) / (line_length * radial_length))
        if alignment >= 0.84:
            accepted.append(((round(x1), round(y1)), (round(x2), round(y2)), alignment))
    if len(accepted) < 5:
        return None
    accepted.sort(key=lambda item: item[2], reverse=True)
    accepted = accepted[:18]
    out = Image.fromarray(rgb.copy(), "RGB")
    draw = ImageDraw.Draw(out, "RGBA")
    stroke = max(2, round(short / 420))
    for start, end, _ in accepted:
        draw.line((start, end), fill=(0, 0, 0, 160), width=stroke * 3)
        draw.line((start, end), fill=(54, 196, 220, 235), width=stroke)
    radius = stroke * 5
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        outline=(203, 126, 235, 240),
        width=stroke,
    )
    return (
        VisualEvidenceArtifact(
            kind=VisualArtifactKind.RADIAL_BLUR,
            authority=VisualArtifactAuthority.LOCATED_MODEL_READ,
            status=VisualArtifactStatus.RENDERED,
            verification=VisualArtifactVerification.BOUNDED,
            label="Radial line convergence",
            legend=(
                "Cyan marks line segments that converge on the violet centre. "
                "This supports a zoom-burst read; it does not prove how the lens moved."
            ),
            metrics={
                "supporting_segment_count": len(accepted),
                "mean_radial_alignment_pct": round(
                    float(np.mean([item[2] for item in accepted])) * 100,
                    1,
                ),
            },
            renderer_version=RENDERER_VERSION,
        ),
        np.asarray(out, dtype=np.uint8),
    )


def _face_landmarks(
    rgb: np.ndarray,
    source: np.ndarray,
    technique_id: str,
) -> tuple[VisualEvidenceArtifact, np.ndarray] | None:
    if not YUNET_MODEL.exists() or not hasattr(cv2, "FaceDetectorYN"):
        return None
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    detector = cv2.FaceDetectorYN.create(
        str(YUNET_MODEL),
        "",
        (320, 320),
        score_threshold=0.72,
        nms_threshold=0.3,
        top_k=250,
    )
    detector.setInputSize((rgb.shape[1], rgb.shape[0]))
    _, detections = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    candidates = []
    for row in detections if detections is not None else []:
        x, y, width, height = (int(round(float(value))) for value in row[:4])
        centre_x = min(gray.shape[1] - 1, max(0, x + width // 2))
        centre_y = min(gray.shape[0] - 1, max(0, y + height // 2))
        if width > 0 and height > 0 and source[centre_y, centre_x]:
            candidates.append((x, y, width, height, row))
    if not candidates:
        return None
    x, y, width, height, face = max(candidates, key=lambda item: item[2] * item[3])
    x = max(0, x)
    y = max(0, y)
    width = min(gray.shape[1] - x, width)
    height = min(gray.shape[0] - y, height)
    landmarks = [(float(face[index]), float(face[index + 1])) for index in range(4, 14, 2)]
    eyes = landmarks[:2]
    out = Image.fromarray(rgb.copy(), "RGB")
    draw = ImageDraw.Draw(out, "RGBA")
    stroke = max(2, round(min(rgb.shape[:2]) / 380))
    draw.rectangle((x, y, x + width, y + height), outline=(54, 196, 220, 235), width=stroke)
    mid_x = x + width / 2
    draw.line(
        (mid_x, y, mid_x, y + height),
        fill=(255, 255, 255, 150),
        width=max(1, stroke // 2),
    )
    eye_radius = max(5, round(width / 24))
    for ex, ey in eyes:
        draw.ellipse(
            (ex - eye_radius, ey - eye_radius, ex + eye_radius, ey + eye_radius),
            outline=(203, 126, 235, 235),
            width=stroke,
        )
    left = gray[y : y + height, x : x + width // 2]
    right = gray[y : y + height, x + width // 2 : x + width]
    return (
        VisualEvidenceArtifact(
            kind=VisualArtifactKind.FACE_LANDMARKS,
            authority=VisualArtifactAuthority.LOCATED_MODEL_READ,
            status=VisualArtifactStatus.RENDERED,
            verification=VisualArtifactVerification.BOUNDED,
            label="Face and light split",
            legend=(
                "Cyan bounds the detected face, violet marks detected eyes, and the white "
                "axis supports side-to-side light comparison."
            ),
            metrics={
                "eye_count": len(eyes),
                "face_detection_confidence": round(float(face[14]), 3),
                "left_face_luma": round(float(np.mean(left)), 1),
                "right_face_luma": round(float(np.mean(right)), 1),
                "technique_context": technique_id,
            },
            renderer_version=RENDERER_VERSION,
        ),
        np.asarray(out, dtype=np.uint8),
    )


def _bokeh(rgb: np.ndarray, source: np.ndarray) -> tuple[VisualEvidenceArtifact, np.ndarray] | None:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 1.8)
    short = min(gray.shape)
    circles = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(8, short // 30),
        param1=90,
        param2=22,
        minRadius=max(3, short // 140),
        maxRadius=max(8, short // 7),
    )
    if circles is None:
        return None
    accepted: list[tuple[int, int, int]] = []
    height, width = gray.shape
    for x, y, radius in np.round(circles[0]).astype(int):
        if not (0 <= x < width and 0 <= y < height and source[y, x]):
            continue
        y0, y1 = max(0, y - radius), min(height, y + radius + 1)
        x0, x1 = max(0, x - radius), min(width, x + radius + 1)
        if float(np.mean(gray[y0:y1, x0:x1])) < 115:
            continue
        accepted.append((x, y, radius))
        if len(accepted) == 24:
            break
    if not accepted:
        return None
    out = Image.fromarray(rgb.copy(), "RGB")
    draw = ImageDraw.Draw(out, "RGBA")
    stroke = max(2, round(short / 350))
    for x, y, radius in accepted:
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            outline=(54, 196, 220, 230),
            width=stroke,
        )
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(54, 196, 220, 230))
    return (
        VisualEvidenceArtifact(
            kind=VisualArtifactKind.BOKEH_INSTANCES,
            authority=VisualArtifactAuthority.LOCATED_MODEL_READ,
            status=VisualArtifactStatus.RENDERED,
            verification=VisualArtifactVerification.BOUNDED,
            label="Candidate bokeh highlights",
            legend=(
                "Cyan circles mark bright soft-disc candidates; the model read still decides "
                "whether they function as bokeh."
            ),
            metrics={"candidate_count": len(accepted)},
            renderer_version=RENDERER_VERSION,
        ),
        np.asarray(out, dtype=np.uint8),
    )


def _clean_mask(mask: np.ndarray, max_components: int = 0) -> np.ndarray:
    data = mask.astype(np.uint8) * 255
    kernel = np.ones((3, 3), np.uint8)
    data = cv2.morphologyEx(data, cv2.MORPH_OPEN, kernel)
    data = cv2.morphologyEx(data, cv2.MORPH_CLOSE, kernel)
    if max_components:
        count, labels, stats, _ = cv2.connectedComponentsWithStats(data, connectivity=8)
        frame_area = data.shape[0] * data.shape[1]
        ranked = sorted(
            (
                (int(stats[index, cv2.CC_STAT_AREA]), index)
                for index in range(1, count)
                if stats[index, cv2.CC_STAT_AREA] >= max(16, frame_area // 12000)
            ),
            reverse=True,
        )[:max_components]
        kept = np.zeros_like(data)
        for _, index in ranked:
            kept[labels == index] = 255
        data = kept
    return data.astype(bool)


def _two_mask_overlay(rgb: np.ndarray, first: np.ndarray, second: np.ndarray) -> np.ndarray:
    out = (rgb.astype(np.float32) * 0.76).astype(np.uint8)
    out = _mask_overlay(out, first, EVIDENCE_CYAN, alpha=0.55, dim=1.0)
    if np.any(second):
        out = _mask_overlay(out, second, EVIDENCE_VIOLET, alpha=0.55, dim=1.0)
    return out


def _mask_overlay(
    rgb: np.ndarray,
    mask: np.ndarray,
    colour: np.ndarray,
    *,
    alpha: float,
    dim: float,
) -> np.ndarray:
    out = (rgb.astype(np.float32) * dim).astype(np.uint8)
    if np.any(mask):
        values = out[mask].astype(np.float32)
        out[mask] = np.clip(values * (1 - alpha) + colour * alpha, 0, 255).astype(np.uint8)
    return out


def _heat_overlay(
    rgb: np.ndarray,
    values: np.ndarray,
    source: np.ndarray,
    *,
    sparse: bool = False,
) -> np.ndarray:
    heat_bgr = cv2.applyColorMap(values.astype(np.uint8), cv2.COLORMAP_TURBO)
    heat = cv2.cvtColor(heat_bgr, cv2.COLOR_BGR2RGB)
    out = (rgb.astype(np.float32) * 0.9).astype(np.uint8)
    if sparse:
        alpha = (values.astype(np.float32) / 255.0 * 0.58)[..., None]
        blended = np.clip(
            rgb.astype(np.float32) * (1 - alpha) + heat.astype(np.float32) * alpha,
            0,
            255,
        )
    else:
        blended = np.clip(
            rgb.astype(np.float32) * 0.66 + heat.astype(np.float32) * 0.34,
            0,
            255,
        )
    out[source] = blended[source].astype(np.uint8)
    return out


def _exif_metrics(shot: Shot) -> dict[str, float | int | str]:
    exif = shot.exif
    metrics: dict[str, float | int | str] = {}
    if exif.exposure_time_s is not None:
        metrics["shutter_s"] = round(exif.exposure_time_s, 6)
    if exif.f_number is not None:
        metrics["aperture_f"] = round(exif.f_number, 2)
    if exif.iso is not None:
        metrics["iso"] = exif.iso
    focal = exif.focal_length_35mm or exif.focal_length_mm
    if focal is not None:
        metrics["focal_mm"] = round(float(focal), 1)
    if exif.flash_fired is not None:
        metrics["flash"] = "fired" if exif.flash_fired else "did not fire"
    return metrics
