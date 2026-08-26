"""Project a stored Analysis into one compact, drawable teaching receipt."""

import re

from app.domain import findings, taxonomy, technique_map
from app.domain.entities import (
    Analysis,
    Move,
    MoveKind,
    Shot,
    ShotTeachingReceipt,
    TeachingAuthority,
)
from app.domain.grid import Grid, GridError

_CELL_SPAN = re.compile(r"\b([A-Z]\d{1,2})(?:\s*[-–]\s*([A-Z]\d{1,2}))?\b")
_MOVE_PRIORITY = {MoveKind.CAMERA: 0, MoveKind.MOVE: 1, MoveKind.CROP: 2}


def build(shot: Shot, analysis: Analysis) -> ShotTeachingReceipt:
    grid = _grid(shot)
    receipt = ShotTeachingReceipt(guide=analysis.composition.guide)
    corroborated = sorted(
        (item for item in analysis.techniques if technique_map.corroborated(item)),
        key=lambda item: (-item.agreement, -item.confidence, item.technique_id),
    )
    if corroborated:
        evidence = corroborated[0]
        technique = taxonomy.BY_ID.get(evidence.technique_id)
        receipt.keep_title = (
            technique.name if technique else evidence.technique_id.replace("_", " ")
        )
        receipt.keep_proof = _compact(
            evidence.note
            or f"{evidence.agreement} independent Analyst lenses corroborated this Technique.",
            grid,
            180,
        )
        receipt.keep_technique_id = evidence.technique_id
        receipt.keep_authority = TeachingAuthority.MODEL_READ
        receipt.keep_cells = list(evidence.cells)

    finding = analysis.findings[0] if analysis.findings else None
    if finding is not None:
        receipt.notice_title = _sentence(_compact(finding.what, grid, 120))
        receipt.notice_proof = _sentence(_compact(finding.why, grid, 180))
        receipt.notice_finding_id = finding.finding_id
        receipt.notice_authority = TeachingAuthority.MEASURED
        receipt.notice_cells = list(finding.cells)
    elif analysis.observations:
        receipt.notice_title = _sentence(_compact(analysis.observations[0], grid, 120))
        receipt.notice_proof = "One Analyst observation; not a measured Finding."
        receipt.notice_authority = TeachingAuthority.MODEL_READ

    move = _primary_move(analysis.composition.moves)
    if move is not None:
        receipt.try_text = _sentence(_compact(move.what, grid, 140))
        receipt.try_reason = _sentence(_compact(move.reason, grid, 180))
        receipt.try_kind = move.kind
        receipt.try_from_cells = list(move.from_cells)
        receipt.try_to_cells = list(move.to_cells)

    receipt.visible_check = _visible_check(finding.finding_id if finding else "", move, grid)
    receipt.primary_layer = _primary_layer(
        finding.finding_id if finding else "", finding.cells if finding else [], move, receipt.guide
    )
    return receipt


def _primary_move(moves: list[Move]) -> Move | None:
    candidates = ((index, move) for index, move in enumerate(moves) if move.what.strip())
    selected = min(
        candidates,
        key=lambda item: (_MOVE_PRIORITY[item[1].kind], item[0]),
        default=None,
    )
    return selected[1] if selected else None


def _visible_check(finding_id: str, move: Move | None, grid: Grid | None) -> str:
    checks = {
        findings.CAMERA_SHAKE: (
            "Zoom into one fine edge after capture; it should stay single rather than "
            "doubled or smeared."
        ),
        findings.BLOWN_HIGHLIGHTS: (
            "Look at the brightest important area; texture should remain visible instead "
            "of pure white."
        ),
        findings.SPLIT_HORIZON: (
            "Check that the horizon no longer cuts through the subject or the frame's middle."
        ),
        findings.OFF_GUIDE_SUBJECT: (
            "Check that the subject meets the selected guide—or that you deliberately reject it."
        ),
        findings.NO_CENTRE_OF_INTEREST: (
            "Name the first subject your eye should land on; it should be visually distinct."
        ),
        findings.COLOUR_CAST: (
            "Check a neutral surface; it should not lean visibly warm or cool unless intentional."
        ),
    }
    if finding_id in checks:
        return checks[finding_id]
    if move is None:
        return ""
    if move.kind is MoveKind.MOVE and move.to_cells and grid is not None:
        place = grid.place(move.to_cells)
        return f"Check that the moved element now sits in {place}." if place else ""
    if move.kind is MoveKind.CROP:
        return "Check all four edges before capture; the distraction should already be outside."
    if move.kind is MoveKind.CAMERA:
        reason = _plain(move.reason, grid).strip().rstrip(".")
        return f"After moving, check the frame again: {reason.lower()}." if reason else ""
    return ""


def _primary_layer(
    finding_id: str,
    finding_cells: list[str],
    move: Move | None,
    guide: str,
) -> str:
    if finding_cells or finding_id in {findings.BLOWN_HIGHLIGHTS, findings.SPLIT_HORIZON}:
        return "finding"
    if move is not None and (
        (move.kind is MoveKind.MOVE and move.from_cells and move.to_cells)
        or (move.kind is MoveKind.CROP and move.to_cells)
    ):
        return "action"
    return "guide" if guide else "clean"


def _plain(text: str, grid: Grid | None) -> str:
    if grid is None:
        return " ".join(text.split())

    def replace(match: re.Match) -> str:
        refs = [value for value in match.groups() if value]
        try:
            place = grid.place(refs)
        except GridError:
            place = ""
        return place or "the marked area"

    return " ".join(_CELL_SPAN.sub(replace, text).split())


def _compact(text: str, grid: Grid | None, limit: int) -> str:
    """Keep one useful sentence in the receipt; the full Analysis remains stored."""
    clean = _plain(text, grid)
    first = re.split(r"(?<=[.!?])\s+", clean, maxsplit=1)[0]
    if len(first) <= limit:
        return first
    clipped = first[: limit + 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}..." if clipped else first[:limit]


def _sentence(text: str) -> str:
    clean = text.strip()
    return clean if not clean or clean.endswith((".", "!", "?")) else f"{clean}."


def _grid(shot: Shot) -> Grid | None:
    if shot.grid is None:
        return None
    return Grid(
        cols=shot.grid.cols,
        rows=shot.grid.rows,
        width=shot.grid.width,
        height=shot.grid.height,
    )
