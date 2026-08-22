"""The Analyst: one shot in, evidence out.

Model boundary rules (AGENTS.md): the model emits cell refs and technique
ids only. ``validate()`` is pure and drops anything outside the grid or the
catalogue, logging what it dropped, before the result is stored.
"""

import logging

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from app.agents import prompts
from app.agents.runtime import bytes_part, run_agent
from app.config import settings
from app.domain import taxonomy
from app.domain.entities import (
    Analysis,
    Composition,
    Exif,
    Move,
    Shot,
    TechniqueEvidence,
    VideoMeta,
)
from app.domain.grid import Grid

logger = logging.getLogger(__name__)


# --- the model's output shape ---------------------------------------------


class EvidenceOut(BaseModel):
    technique_id: str
    confidence: float = Field(ge=0, le=1)
    cells: list[str] = Field(default_factory=list)
    note: str = ""


class MoveOut(BaseModel):
    what: str
    from_cells: list[str] = Field(default_factory=list)
    to_cells: list[str] = Field(default_factory=list)
    reason: str = ""


class CompositionOut(BaseModel):
    subject_cells: list[str] = Field(default_factory=list)
    horizon_row: int | None = None
    suggested_crop_cells: list[str] = Field(default_factory=list)
    moves: list[MoveOut] = Field(default_factory=list)


class AnalystOutput(BaseModel):
    techniques: list[EvidenceOut] = Field(default_factory=list)
    composition: CompositionOut = Field(default_factory=CompositionOut)
    critique: str = ""
    score: int = Field(default=5, ge=1, le=10)


# --- agent ----------------------------------------------------------------


def analyst_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="analyst",
        description="Reads one shot and reports technique evidence, composition and a critique.",
        instruction=prompts.load("analyst"),
        output_schema=AnalystOutput,
        output_key="analysis",
    )


def catalogue_text(video: bool) -> str:
    """The technique list the model may pick from, with cues."""
    lines = []
    for t in taxonomy.TECHNIQUES:
        if t.video_only and not video:
            continue
        lines.append(f"- `{t.id}` ({t.family.value}, L{t.level}): {t.cue}")
    return "\n".join(lines)


def facts_text(exif: Exif, video: VideoMeta | None) -> str:
    facts = []
    if video:
        facts.append(f"video: {video.width}x{video.height}, {video.duration_s:.1f} s")
        if video.fps:
            facts.append(f"frame rate: {video.fps:g} fps")
        if video.lufs is not None:
            facts.append(f"loudness: {video.lufs:.1f} LUFS")
    if exif.exposure_time_s:
        facts.append(f"shutter: {_shutter(exif.exposure_time_s)}")
    if exif.f_number:
        facts.append(f"aperture: f/{exif.f_number:g}")
    if exif.iso:
        facts.append(f"ISO {exif.iso}")
    if exif.focal_length_35mm:
        facts.append(f"focal length: {exif.focal_length_35mm} mm (35 mm equivalent)")
    elif exif.focal_length_mm:
        facts.append(f"focal length: {exif.focal_length_mm:g} mm")
    if exif.flash_fired is not None:
        facts.append("flash fired" if exif.flash_fired else "no flash")
    if exif.make or exif.model:
        facts.append(f"camera: {exif.make} {exif.model}".strip())
    return "\n".join(f"- {f}" for f in facts) or "- none available"


def _shutter(seconds: float) -> str:
    if seconds >= 1:
        return f"{seconds:g} s"
    return f"1/{round(1 / seconds)} s"


def prompt_for(shot: Shot) -> str:
    grid = shot.grid
    video = shot.kind.value == "video"
    return (
        f"Grid: {grid.cols} columns x {grid.rows} rows "
        f"(cells A1 to {chr(ord('A') + grid.cols - 1)}{grid.rows}).\n"
        f"Shot kind: {'video contact sheet' if video else 'photo'}.\n\n"
        f"Camera facts:\n{facts_text(shot.exif, shot.video)}\n\n"
        f"Technique catalogue:\n{catalogue_text(video)}"
    )


async def analyse(shot: Shot, gridded_png: bytes) -> AnalystOutput:
    return await run_agent(
        analyst_agent(),
        prompt=prompt_for(shot),
        images=[bytes_part(gridded_png, "image/png")],
        schema=AnalystOutput,
        user_id=shot.user_id,
    )


# --- validation (pure) ----------------------------------------------------


def validate(shot: Shot, raw: AnalystOutput) -> Analysis:
    """Keep only what the grid and the catalogue can vouch for."""
    grid = Grid(
        cols=shot.grid.cols, rows=shot.grid.rows, width=shot.grid.width, height=shot.grid.height
    )
    video = shot.kind.value == "video"

    techniques: list[TechniqueEvidence] = []
    seen: set[str] = set()
    for item in raw.techniques:
        tid = item.technique_id.strip().lower()
        if tid not in taxonomy.BY_ID:
            logger.warning(
                "analyst: dropped unknown technique %r on %s", item.technique_id, shot.id
            )
            continue
        if taxonomy.BY_ID[tid].video_only and not video:
            logger.warning("analyst: dropped video technique %r on a photo %s", tid, shot.id)
            continue
        if tid in seen:
            continue
        seen.add(tid)
        techniques.append(
            TechniqueEvidence(
                technique_id=tid,
                confidence=max(0.0, min(1.0, item.confidence)),
                cells=_cells(grid, item.cells),
                note=item.note.strip()[:300],
            )
        )

    moves = [
        Move(
            what=m.what.strip()[:80],
            from_cells=_cells(grid, m.from_cells),
            to_cells=_cells(grid, m.to_cells),
            reason=m.reason.strip()[:300],
        )
        for m in raw.composition.moves[:3]
        if m.what.strip()
    ]
    moves = [m for m in moves if m.from_cells or m.to_cells]

    horizon = raw.composition.horizon_row
    if horizon is not None and not (1 <= horizon <= grid.rows):
        horizon = None

    return Analysis(
        shot_id=shot.id,
        user_id=shot.user_id,
        model=settings.model_flash,
        techniques=techniques,
        composition=Composition(
            subject_cells=_cells(grid, raw.composition.subject_cells),
            horizon_row=horizon,
            suggested_crop_cells=_cells(grid, raw.composition.suggested_crop_cells),
            moves=moves,
        ),
        critique=raw.critique.strip()[:2000],
        score=max(1, min(10, raw.score)),
    )


def _cells(grid: Grid, refs: list[str]) -> list[str]:
    out: list[str] = []
    for ref in refs:
        cleaned = ref.strip().upper()
        if grid.contains(cleaned) and cleaned not in out:
            out.append(cleaned)
    return out
