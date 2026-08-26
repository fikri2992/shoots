"""Project a stored Analysis into one compact, drawable teaching receipt."""

import re

from app.domain import findings, taxonomy, technique_map
from app.domain.entities import (
    Analysis,
    Move,
    MoveKind,
    MoveWarrant,
    Shot,
    ShotTeachingReceipt,
    TeachingAuthority,
)
from app.domain.grid import Grid, GridError

_CELL_SPAN = re.compile(
    r"\b(?:(?:cells?|rows?|columns?)\s+)?([A-Z]\d{1,2})"
    r"(?:\s*(?:-|–|through|to)\s*([A-Z]\d{1,2}))?\b",
    re.IGNORECASE,
)
_ROW_SPAN = re.compile(
    r"\brows?\s+(\d{1,2})(?:\s*(?:-|–|through|to|and)\s*(\d{1,2}))?\b",
    re.IGNORECASE,
)
_COLUMN_SPAN = re.compile(
    r"\bcolumns?\s+([A-Z])(?:\s*(?:-|–|through|to|and)\s*([A-Z]))?\b",
    re.IGNORECASE,
)
_MOVE_PRIORITY = {MoveKind.CAMERA: 0, MoveKind.MOVE: 1, MoveKind.CROP: 2}
_STOPWORDS = {
    "about",
    "after",
    "against",
    "because",
    "before",
    "frame",
    "from",
    "into",
    "should",
    "subject",
    "that",
    "their",
    "this",
    "through",
    "with",
}


def build(shot: Shot, analysis: Analysis) -> ShotTeachingReceipt:
    grid = _grid(shot)
    receipt = ShotTeachingReceipt(guide=analysis.composition.guide)
    keep_focus = ""
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
        keep_focus = f"{evidence.note} {technique.cue if technique else ''}"

    finding = analysis.findings[0] if analysis.findings else None
    move = _primary_move(
        analysis.composition.moves,
        allow_crop=not corroborated or finding is not None,
        protected_technique_ids={item.technique_id for item in corroborated[:1]},
    )
    if finding is not None:
        receipt.notice_title = _sentence(_compact(finding.what, grid, 120))
        receipt.notice_proof = _sentence(_compact(finding.why, grid, 180))
        receipt.notice_finding_id = finding.finding_id
        receipt.notice_authority = TeachingAuthority.MEASURED
        receipt.notice_cells = list(finding.cells)
    elif analysis.observations:
        observation = _aligned_observation(analysis.observations, move, keep_focus)
        receipt.notice_title = _sentence(
            _compact(_without_grid_locators(observation), None, 160, first_clause=True)
        )
        receipt.notice_proof = "One Analyst observation; not a measured Finding."
        receipt.notice_authority = TeachingAuthority.MODEL_READ

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


def _primary_move(
    moves: list[Move],
    *,
    allow_crop: bool,
    protected_technique_ids: set[str],
) -> Move | None:
    candidates = (
        (index, move)
        for index, move in enumerate(moves)
        if move.what.strip()
        and (allow_crop or move.kind is not MoveKind.CROP)
        and move.warrant not in {MoveWarrant.GUIDE, MoveWarrant.VARIATION}
        and not protected_technique_ids.intersection(move.challenges_technique_ids)
    )
    selected = min(
        candidates,
        key=lambda item: (_MOVE_PRIORITY[item[1].kind], item[0]),
        default=None,
    )
    return selected[1] if selected else None


def _aligned_observation(
    observations: list[str],
    move: Move | None,
    keep_focus: str,
) -> str:
    """Prefer the observation that explains the selected action, preserving source text."""
    focus = f"{move.what} {move.reason}" if move is not None else keep_focus
    if not focus:
        return observations[0]
    wanted = _keywords(focus)
    if not wanted:
        return observations[0]
    return max(
        enumerate(observations),
        key=lambda item: (
            len(wanted & _keywords(item[1])),
            -len(item[1]),
            -item[0],
        ),
    )[1]


def _keywords(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z]{4,}", text.lower())
        if word not in _STOPWORDS
    }


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
        reason = move.reason.lower()
        conflict_words = ("cross", "cut", "overlap", "distract", "compete", "trap")
        if any(word in reason for word in conflict_words):
            return (
                "After changing viewpoint, check that the background no longer crosses "
                "or competes with the subject."
            )
        return (
            "After changing viewpoint, compare the subject's separation and every frame edge."
        )
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
        refs = [value.upper() for value in match.groups() if value]
        try:
            place = grid.place(refs)
        except GridError:
            place = ""
        return place or "the marked area"

    clean = _CELL_SPAN.sub(replace, text)
    clean = _ROW_SPAN.sub(lambda match: _axis_place(match, grid.rows, "row"), clean)
    clean = _COLUMN_SPAN.sub(lambda match: _axis_place(match, grid.cols, "column"), clean)
    clean = re.sub(
        r"\b(?:top|upper)\s+(?:one|two|three|\d+)?\s*rows?\b",
        "top of the frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?:bottom|lower)\s+(?:one|two|three|\d+)?\s*rows?\b",
        "bottom of the frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?:cells?|rows?|columns?)\b",
        "area",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?:from|through)\s+((?:across|down)\s+the)\b",
        r"\1",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bacross\s+(?:across|down)\s+the\b",
        "across the",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bmarked area\s+(most of the frame|(?:across|down)\s+the\s+\w+)\b",
        r"\1",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?:the\s+)?(?:upper|top)\s+portion\s+across\s+the\s+top\b",
        "the top of the frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?:the\s+)?(?:lower|bottom)\s+portion\s+across\s+the\s+bottom\b",
        "the bottom of the frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\s*\((?:across|down)\s+the\s+"
        r"(?:top|middle|bottom|left|centre|right)(?:\s+of\s+the\s+frame)?\)",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(across\s+the\s+(?:top|middle|bottom|left|centre|right))"
        r"(?:\s+of\s+the\s+frame)?\s+\1\b",
        r"\1 of the frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bacross\s+the\s+top\s+in\s+the\s+upper\s+third\b",
        "across the upper third",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?P<axis>left|right|top|bottom)\s+"
        r"(?P<depth>foreground|background)\s+"
        r"(?:across|down)\s+the\s+[^,.;]+",
        r"\g<axis> \g<depth>",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bcentre\s+of\s+the\s+frame\s+across\s+the\s+middle\b",
        "centre of the frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\boccupies\s+down\s+the\s+(left|right|centre)\b",
        r"occupies the \1 side of the frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\boccupy\s+down\s+the\s+(left|right|centre)\b",
        r"occupy the \1 side of the frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bon\s+the\s+(left|right)\s+down\s+the\s+\1\b",
        r"on the \1 side of the frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?:the\s+)?upper\s+portion\s+of\s+the\s+frame\s+"
        r"in\s+the\s+top\s+of\s+the\s+frame\s+across\s+the\s+top\b",
        "the upper frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?:the\s+)?upper\s+frame\s+horizontally\s+across\s+the\s+top\s+of\s+the\s+frame\b",
        "horizontally across the upper frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bcentral\s+foreground\s+across\s+the\s+centre\b",
        "central foreground",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\balong\s+the\s+(top|bottom)\s+of\s+the\s+frame\s+"
        r"(?:across|along)\s+the\s+\1(?:\s+of\s+the\s+frame)?\b",
        r"along the \1 of the frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bupper\s+frame\s+in\s+the\s+top\s+of\s+the\s+frame\b",
        "upper frame",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?:in|from)\s+(?:area\s+)?(?:the\s+)?bottom(?:\s+left|\s+right)?\s+"
        r"and\s+across\s+the\s+bottom\b",
        "across the bottom",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bin\s+across\s+the\s+(top|middle|bottom|left|centre|right)\b",
        r"across the \1",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\bthe\s+(left|right|top|bottom)\s+of\s+the\s+frame\s+contain\b",
        r"the \1 of the frame contains",
        clean,
        flags=re.IGNORECASE,
    )
    return " ".join(clean.split())


def _without_grid_locators(text: str) -> str:
    """Remove the Analyst's addressing syntax from one image-led observation.

    The selected image layer already points to the region. Translating every grid
    span into prose often repeats or contradicts the sentence's own spatial words.
    """
    clean = _CELL_SPAN.sub("", text)
    clean = _ROW_SPAN.sub("", clean)
    clean = _COLUMN_SPAN.sub("", clean)
    clean = re.sub(r"\b(?:cells?|rows?|columns?)\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(
        r"\s+\b(?:in|at|from|across|along|into|within)\s+(?:and\s+)?"
        r"(?=(?:while|with|against|and\b|[,.;]|$))",
        " ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(r"\s+and\s+(?=(?:while|with|against|[,.;]|$))", " ", clean)
    clean = re.sub(
        r"\b(?:along|across|from|in|at|into|within|spanning|stretching)\s*"
        r"(?=(?:with\b|[,.;]|$))",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?:in|at|from|across|along|into|within)\s+"
        r"(?=(?:is|are|was|were|shows?|exhibits?|remains?)\b)",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?:at|in|within)\s+"
        r"(?=(?:on|beneath|above|below|behind|before|after|against)\b)",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(?:running|spanning|stretching)\s+(?:across|along)?\s*"
        r"(?=[,.;]|$)",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(r"\s+([,.;])", r"\1", clean)
    clean = re.sub(r",\s*(?:and\s*)?\.", ".", clean)
    return " ".join(clean.split())


def _axis_place(match: re.Match, size: int, axis: str) -> str:
    first, last = match.groups()
    if axis == "row":
        start = int(first) - 1
        end = int(last or first) - 1
    else:
        start = ord(first.upper()) - ord("A")
        end = ord((last or first).upper()) - ord("A")
    low, high = sorted((max(0, start), min(size - 1, end)))
    share = (high - low + 1) / size
    if share > 0.6:
        return "most of the frame"
    centre = (low + high + 1) / 2 / size
    if axis == "row":
        place = "top" if centre < 1 / 3 else "bottom" if centre > 2 / 3 else "middle"
    else:
        place = "left" if centre < 1 / 3 else "right" if centre > 2 / 3 else "centre"
    return f"the {place} of the frame"


def _compact(
    text: str,
    grid: Grid | None,
    limit: int,
    *,
    first_clause: bool = False,
) -> str:
    """Keep one useful sentence in the receipt; the full Analysis remains stored."""
    clean = _plain(text, grid)
    first = re.split(r"(?<=[.!?])\s+", clean, maxsplit=1)[0]
    if first_clause:
        clause = re.split(r";", first, maxsplit=1)[0].strip()
        if len(clause) >= 24:
            first = clause
    if len(first) <= limit:
        return first
    clipped = first[: limit + 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}..." if clipped else first[:limit]


def _sentence(text: str) -> str:
    clean = text.strip()
    if not clean:
        return ""
    clean = clean[0].upper() + clean[1:]
    return clean if clean.endswith((".", "!", "?")) else f"{clean}."


def _grid(shot: Shot) -> Grid | None:
    if shot.grid is None:
        return None
    return Grid(
        cols=shot.grid.cols,
        rows=shot.grid.rows,
        width=shot.grid.width,
        height=shot.grid.height,
    )
