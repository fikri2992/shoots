"""Pure Evidence selection and validation for a selected Shot's social story."""

import math
import re

from app.domain import taxonomy
from app.domain.entities import (
    Analysis,
    DeconstructionEvidence,
    DeconstructionPage,
    DeconstructionPageKind,
    DeconstructionStory,
    Shot,
    VisualArtifactAuthority,
    VisualArtifactKind,
    VisualArtifactStatus,
    VisualArtifactVerification,
    VisualEvidenceArtifact,
)
from app.domain.grid import Grid

PLAN_VERSION = "deconstruction-selected-shot-6"
DETAIL_ASPECT = 1.4
_CELL = re.compile(r"\b[A-Z]\d{1,2}\b")
_INTERNAL = re.compile(
    r"\b(?:keeper|criteria|verdict|evidence|shot_id|shoot record|"
    r"experiment record|analysis|technique map)\b",
    re.IGNORECASE,
)
_FIRST_PERSON = re.compile(r"\b(?:I|I've|I'm|my|we|our)\b", re.IGNORECASE)
_TIME_OF_DAY = re.compile(
    r"\b(?:morning|afternoon|evening|dawn|dusk|sunrise|sunset|twilight|nighttime)\b",
    re.IGNORECASE,
)


class UnsupportedStory(ValueError):
    """A structurally unsupported draft; never silently replaced by a template."""


def cover_candidates(shots: list[Shot]) -> list[str]:
    return [shot.id for shot in shots if shot.kept_at is not None and shot.kind.value == "photo"]


def evidence_for(
    shot: Shot,
    analysis: Analysis,
    *,
    max_items: int,
    min_agreement: int,
    min_confidence: float,
    max_details: int,
    source_digest: str = "",
    artifact_renderer_version: str = "",
) -> list[DeconstructionEvidence]:
    if analysis.shot_id != shot.id or analysis.user_id != shot.user_id:
        raise UnsupportedStory("The stored reading does not belong to this Shot.")
    if analysis.abstained:
        raise UnsupportedStory("This Shot does not yet have a usable visual reading.")
    grid = Grid(**shot.grid.model_dump()) if shot.grid else None
    evidence: list[DeconstructionEvidence] = []
    for index, observation in enumerate(analysis.observations):
        if not observation.strip():
            continue
        evidence.append(
            DeconstructionEvidence(
                id=f"observation_{index + 1}",
                shot_id=shot.id,
                text=observation.strip(),
                source_ref=f"analysis:{shot.id}:observation:{index}",
                cells=_detail_cells(_CELL.findall(observation), grid),
            )
        )
    for item in analysis.techniques:
        if (
            item.technique_id not in taxonomy.BY_ID
            or item.agreement < min_agreement
            or item.confidence < min_confidence
            or not item.note.strip()
        ):
            continue
        # A relational claim needs the whole image. Never flatten its semantic
        # members into a convenient but misleading local crop.
        cells = [] if item.paths or item.regions else _detail_cells(item.cells, grid)
        evidence.append(
            DeconstructionEvidence(
                id=f"technique_{item.technique_id}",
                shot_id=shot.id,
                text=item.note.strip(),
                source_ref=f"analysis:{shot.id}:technique:{item.technique_id}",
                cells=cells,
                visual_artifact=(
                    item.visual_artifact.model_copy(deep=True)
                    if artifact_is_eligible(
                        item.visual_artifact, source_digest, artifact_renderer_version
                    )
                    and subject_extent_is_supported(item.visual_artifact, analysis, grid)
                    else None
                ),
            )
        )
    evidence = list({item.id: item for item in evidence}.values())[:max_items]
    seen_details: set[tuple[int, int, int, int]] = set()
    for item in evidence:
        if item.cells and grid:
            box = grid.context_bounds(item.cells, DETAIL_ASPECT).as_tuple()
            if box in seen_details or len(seen_details) >= max_details:
                item.cells = []
            else:
                seen_details.add(box)
    if not evidence:
        raise UnsupportedStory(
            "This Shot needs a stored visual reading before a story can be made."
        )
    return evidence


def artifact_is_eligible(
    artifact: VisualEvidenceArtifact | None, source_digest: str, renderer_version: str
) -> bool:
    """Metadata admission only; the service must also validate ownership and bytes."""
    if (
        artifact is None
        or not source_digest
        or not renderer_version
        or artifact.source_digest != source_digest
        or artifact.renderer_version != renderer_version
        or artifact.status is not VisualArtifactStatus.RENDERED
        or not artifact.blob_path
        or artifact.fallback_reason
    ):
        return False
    return (
        artifact.authority is VisualArtifactAuthority.MEASURED
        and artifact.verification is VisualArtifactVerification.MEASURED
    ) or (
        artifact.authority
        in {
            VisualArtifactAuthority.LOCATED_MODEL_READ,
            VisualArtifactAuthority.RELATIONAL_MODEL_READ,
        }
        and artifact.verification is VisualArtifactVerification.BOUNDED
    )


def _detail_cells(cells: list[str], grid: Grid | None) -> list[str]:
    if grid is None or grid.width <= 0 or grid.height <= 0:
        return []
    refs = list(dict.fromkeys(cell.upper() for cell in cells if grid.contains(cell.upper())))
    if not refs:
        return []
    box = grid.context_bounds(refs, DETAIL_ASPECT)
    area = box.width * box.height / (grid.width * grid.height)
    # Near-full-frame crops add no useful detail; tiny crops cannot carry a page.
    return refs if 0.04 <= area <= 0.7 else []


def subject_extent_is_supported(
    artifact: VisualEvidenceArtifact, analysis: Analysis, grid: Grid | None
) -> bool:
    """Reject a contour whose measured size contradicts the located subject.

    Technique cells can describe empty space, not the subject. The contour
    renderer's bounded result alone cannot resolve that semantic mismatch.
    """
    if artifact.kind is not VisualArtifactKind.SUBJECT_CONTOUR:
        return True
    if grid is None or grid.width <= 0 or grid.height <= 0:
        return False
    cells = [cell for cell in analysis.composition.subject_cells if grid.contains(cell)]
    if not cells:
        return False
    try:
        measured = float(artifact.metrics["frame_occupancy_pct"])
    except (KeyError, ValueError, TypeError):
        return False
    bounds = grid.zoom_bounds(cells)
    maximum = 100 * bounds.width * bounds.height / (grid.width * grid.height)
    return math.isfinite(measured) and 0 <= measured <= round(maximum, 1)


def story_pages(
    story: DeconstructionStory,
    evidence: list[DeconstructionEvidence],
    cover_shot_id: str,
    *,
    max_beats: int,
) -> list[DeconstructionPage]:
    """Check provenance/structure, not the semantic truth of model prose."""
    if story.abstained or story.opening is None:
        raise UnsupportedStory("The writer could not support a story from this Shot's reading.")
    if not 1 <= len(story.beats) <= max_beats:
        raise UnsupportedStory("The writer returned an unsupported number of story pages.")
    available = {item.id: item for item in evidence if item.shot_id == cover_shot_id}
    if story.opening.detail_evidence_id or story.opening.artifact_evidence_id:
        raise UnsupportedStory("The opening must preserve the full, unmarked Shot.")
    _check_copy(story.caption)
    _references(story.caption_evidence_ids, available)
    pages: list[DeconstructionPage] = []
    seen_titles: set[str] = set()
    seen_bodies: set[str] = set()
    for index, beat in enumerate([story.opening, *story.beats]):
        _check_copy(beat.title)
        _check_copy(beat.body)
        title = " ".join(beat.title.lower().split())
        body = " ".join(beat.body.lower().split())
        if title in seen_titles or body in seen_bodies:
            raise UnsupportedStory(
                "The writer repeated a page instead of adding a new observation."
            )
        seen_titles.add(title)
        seen_bodies.add(body)
        refs = _references(beat.evidence_ids, available)
        detail_cells: list[str] = []
        selected_artifact: DeconstructionEvidence | None = None
        if beat.detail_evidence_id and beat.artifact_evidence_id:
            raise UnsupportedStory("A page must choose one visual explanation, not stack them.")
        if beat.detail_evidence_id:
            detail = available.get(beat.detail_evidence_id)
            if detail is None or detail.id not in beat.evidence_ids or not detail.cells:
                raise UnsupportedStory("The writer selected an unsupported image detail.")
            detail_cells = detail.cells
        if beat.artifact_evidence_id:
            selected_artifact = available.get(beat.artifact_evidence_id)
            if (
                selected_artifact is None
                or selected_artifact.id not in beat.evidence_ids
                or selected_artifact.visual_artifact is None
                or not re.fullmatch(r"[0-9a-f]{64}", selected_artifact.artifact_sha256)
            ):
                raise UnsupportedStory("The writer selected an unavailable visual artifact.")
            refs.append(
                f"{selected_artifact.source_ref}:visual_artifact:{selected_artifact.artifact_sha256}"
            )
        pages.append(
            DeconstructionPage(
                kind=DeconstructionPageKind.COVER if index == 0 else DeconstructionPageKind.STORY,
                title=" ".join(beat.title.split()),
                claim=" ".join(beat.body.split()),
                shot_ids=[cover_shot_id],
                evidence_refs=refs,
                visual_layer=(
                    "artifact" if selected_artifact else "detail" if detail_cells else "original"
                ),
                detail_cells=detail_cells,
                artifact_evidence_id=selected_artifact.id if selected_artifact else "",
                visual_artifact=selected_artifact.visual_artifact if selected_artifact else None,
                artifact_sha256=selected_artifact.artifact_sha256 if selected_artifact else "",
            )
        )
    pages.append(
        DeconstructionPage(
            kind=DeconstructionPageKind.CLEAN,
            title="",
            claim="",
            shot_ids=[cover_shot_id],
            evidence_refs=[f"shot:{cover_shot_id}:original"],
            visual_layer="original",
        )
    )
    return pages


def _references(ids: list[str], available: dict[str, DeconstructionEvidence]) -> list[str]:
    if not ids or any(item not in available for item in ids):
        raise UnsupportedStory("The writer cited Evidence that was not supplied for this Shot.")
    return list(dict.fromkeys(available[item].source_ref for item in ids))


def _check_copy(text: str) -> None:
    if not text.strip() or _CELL.search(text) or _INTERNAL.search(text):
        raise UnsupportedStory("The draft contains empty copy or internal report language.")
    if _FIRST_PERSON.search(text):
        raise UnsupportedStory("The draft speaks for the photographer without their words.")
    if _TIME_OF_DAY.search(text):
        raise UnsupportedStory("The draft inferred a time of day from visual reads alone.")
