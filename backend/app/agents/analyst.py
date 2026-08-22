"""The Analyst: one shot in, evidence out, by a panel of three lenses.

An ADK ``SequentialAgent``: a ``ParallelAgent`` runs the Technician, the
Composer and the Storyteller concurrently on the same shot (each with its
own instruction and its own view of the inputs), then a Synthesizer writes
the critique from their three readings. Deciding *what the frame shows* is
not left to any of them: ``domain/panel.py`` takes the vote, and
``validate()`` keeps only grid cells and catalogue ids (AGENTS.md: the
model boundary is pure and tested).
"""

import logging
from dataclasses import dataclass, field

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from pydantic import BaseModel, Field

from app.agents import prompts
from app.agents.runtime import WorkflowResult, bytes_part, run_workflow
from app.config import settings
from app.domain import exposure, panel, rubric, taxonomy
from app.domain.entities import (
    Analysis,
    Composition,
    Exif,
    Move,
    Shot,
    VideoMeta,
)
from app.domain.grid import Grid

logger = logging.getLogger(__name__)


# --- the lenses' output shapes ----------------------------------------------


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


# Element scores are explicit, required fields per lens, not a dict: Gemini's
# response schema has no additionalProperties (a dict is silently never
# filled) and an optional field is too easily skipped.


class TechnicianElements(BaseModel):
    technical: int = Field(ge=1, le=10)


class ComposerElements(BaseModel):
    composition: int = Field(ge=1, le=10)
    lighting: int = Field(ge=1, le=10)


class StorytellerElements(BaseModel):
    impact: int = Field(ge=1, le=10)
    story: int = Field(ge=1, le=10)


class LensOut(BaseModel):
    observations: list[str] = Field(default_factory=list)
    techniques: list[EvidenceOut] = Field(default_factory=list)
    elements: BaseModel
    note: str = ""


class TechnicianOut(LensOut):
    elements: TechnicianElements


class ComposerOut(LensOut):
    elements: ComposerElements
    composition: CompositionOut = Field(default_factory=CompositionOut)
    #: Video only: up to two timestamps whose exact frames would settle a camera move.
    scrub_seconds: list[float] = Field(default_factory=list)


class StorytellerOut(LensOut):
    elements: StorytellerElements


class SynthesisOut(BaseModel):
    critique: str = ""


SCHEMAS: dict[str, type[LensOut]] = {
    panel.TECHNICIAN: TechnicianOut,
    panel.COMPOSER: ComposerOut,
    panel.STORYTELLER: StorytellerOut,
}


@dataclass
class PanelResult:
    reads: dict[str, LensOut] = field(default_factory=dict)
    synthesis: SynthesisOut | None = None
    #: Seconds each lens took; missing lenses are absent.
    latency: dict[str, float] = field(default_factory=dict)


# --- agents ---------------------------------------------------------------------


def lens_agent(name: str) -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name=name,
        description=f"The {name} lens of the Analyst panel.",
        instruction=prompts.load(name),
        output_schema=SCHEMAS[name],
        output_key=name,
    )


def synthesizer_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="synthesizer",
        description="Writes the critique from the three lenses' readings.",
        instruction=prompts.load("synthesizer"),
        output_schema=SynthesisOut,
        output_key="synthesis",
    )


def analyst_agent() -> SequentialAgent:
    """panel (parallel, three lenses) → synthesizer. Deterministic order."""
    return SequentialAgent(
        name="analyst",
        description="Reads one shot with a panel of three lenses, then writes the critique.",
        sub_agents=[
            ParallelAgent(
                name="panel",
                description="Technician, Composer and Storyteller read the shot concurrently.",
                sub_agents=[lens_agent(lens) for lens in panel.PANEL],
            ),
            synthesizer_agent(),
        ],
    )


# --- prompt pieces ---------------------------------------------------------------


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
    derived = exposure.describe(exif)
    text = "\n".join(f"- {f}" for f in facts) or "- none available"
    if derived:
        text += "\nDerived (arithmetic, not opinion):\n" + "\n".join(f"- {d}" for d in derived)
    return text


def _shutter(seconds: float) -> str:
    if seconds >= 1:
        return f"{seconds:g} s"
    return f"1/{round(1 / seconds)} s"


def prompt_for(shot: Shot) -> str:
    """The user turn every lens sees: the grid, the kind, the catalogue.
    Camera facts go only to the Technician, through its instruction."""
    grid = shot.grid
    video = shot.kind.value == "video"
    return (
        f"Grid: {grid.cols} columns x {grid.rows} rows "
        f"(cells A1 to {chr(ord('A') + grid.cols - 1)}{grid.rows}).\n"
        f"Shot kind: {'video contact sheet' if video else 'photo'}.\n"
        "Image 1 is the gridded frame; Image 2 is the clean frame.\n\n"
        f"Technique catalogue:\n{catalogue_text(video)}"
    )


def state_for(shot: Shot) -> dict[str, str]:
    """Session state the instructions template from: facts for the
    Technician only, anchors for every lens."""
    return {
        "facts": facts_text(shot.exif, shot.video),
        "anchors": rubric.anchors_text(),
    }


async def analyse(shot: Shot, gridded_png: bytes, clean_jpeg: bytes) -> PanelResult:
    result: WorkflowResult = await run_workflow(
        analyst_agent(),
        prompt=prompt_for(shot),
        images=[bytes_part(gridded_png, "image/png"), bytes_part(clean_jpeg, "image/jpeg")],
        state=state_for(shot),
        outputs={**{lens: SCHEMAS[lens] for lens in panel.PANEL}, "synthesis": SynthesisOut},
        user_id=shot.user_id,
        timeout=settings.panel_timeout_seconds,
    )
    reads = {lens: result.outputs[lens] for lens in panel.PANEL if lens in result.outputs}
    if len(reads) < settings.panel_quorum:
        raise RuntimeError(
            f"analyst panel quorum not met: {sorted(reads)} answered "
            f"({', '.join(f'{k}: {v}' for k, v in result.errors.items()) or 'no errors logged'})"
        )
    return PanelResult(
        reads=reads,
        synthesis=result.outputs.get("synthesis"),
        latency={k: v for k, v in result.latency.items() if k in panel.PANEL},
    )


# --- validation (pure) ----------------------------------------------------------


def lens_read(shot: Shot, lens: str, raw: LensOut) -> panel.LensRead:
    """One lens's output with only grid cells and catalogue ids kept."""
    grid = _grid(shot)
    video = shot.kind.value == "video"
    sightings: list[panel.Sighting] = []
    seen: set[str] = set()
    for item in raw.techniques:
        tid = item.technique_id.strip().lower()
        if tid not in taxonomy.BY_ID:
            logger.warning(
                "%s: dropped unknown technique %r on %s", lens, item.technique_id, shot.id
            )
            continue
        if taxonomy.BY_ID[tid].video_only and not video:
            logger.warning("%s: dropped video technique %r on a photo %s", lens, tid, shot.id)
            continue
        if tid in seen:
            continue
        seen.add(tid)
        sightings.append(
            panel.Sighting(
                technique_id=tid,
                confidence=max(0.0, min(1.0, item.confidence)),
                cells=tuple(_cells(grid, item.cells)),
                note=item.note.strip()[:300],
            )
        )
    elements = {
        k: rubric.clamp(v)
        for k, v in raw.elements.model_dump().items()
        if k in panel.LENS_ELEMENTS.get(lens, ()) and v is not None
    }
    observations = [" ".join(o.split())[:240] for o in raw.observations if o.strip()][:6]
    return panel.LensRead(
        lens=lens, sightings=sightings, elements=elements, observations=observations
    )


def validate(shot: Shot, result: PanelResult) -> Analysis:
    """The vote, then only what the grid and the catalogue can vouch for."""
    grid = _grid(shot)
    reads = [lens_read(shot, lens, raw) for lens, raw in result.reads.items()]
    consensus = panel.aggregate(
        reads,
        min_confidence=settings.panel_min_confidence,
        min_agreement=settings.panel_min_agreement,
        owner_confidence=settings.panel_owner_confidence,
        quorum=settings.panel_quorum,
    )
    for lens, tid, confidence in consensus.dissent:
        logger.info(
            "panel: %s alone saw %s at %.2f on %s; not counted", lens, tid, confidence, shot.id
        )

    composer = result.reads.get(panel.COMPOSER)
    raw_comp = composer.composition if isinstance(composer, ComposerOut) else CompositionOut()
    moves = [
        Move(
            what=m.what.strip()[:80],
            from_cells=_cells(grid, m.from_cells),
            to_cells=_cells(grid, m.to_cells),
            reason=m.reason.strip()[:300],
        )
        for m in raw_comp.moves[:3]
        if m.what.strip()
    ]
    moves = [m for m in moves if m.from_cells or m.to_cells]
    horizon = raw_comp.horizon_row
    if horizon is not None and not (1 <= horizon <= grid.rows):
        horizon = None

    critique = (result.synthesis.critique if result.synthesis else "").strip()
    if not critique:
        critique = " ".join(r.note.strip() for r in result.reads.values() if r.note.strip())

    return Analysis(
        shot_id=shot.id,
        user_id=shot.user_id,
        model=settings.model_flash,
        techniques=consensus.techniques,
        composition=Composition(
            subject_cells=_cells(grid, raw_comp.subject_cells),
            horizon_row=horizon,
            suggested_crop_cells=_cells(grid, raw_comp.suggested_crop_cells),
            moves=moves,
        ),
        observations=consensus.observations,
        elements=consensus.elements,
        critique=critique[:2000],
        score=rubric.overall(consensus.elements),
        panel={lens: round(result.latency.get(lens, 0.0), 1) for lens in result.reads},
        dissent=[
            {"lens": lens, "technique_id": tid, "confidence": round(conf, 2)}
            for lens, tid, conf in consensus.dissent
        ],
    )


def _grid(shot: Shot) -> Grid:
    return Grid(
        cols=shot.grid.cols, rows=shot.grid.rows, width=shot.grid.width, height=shot.grid.height
    )


def _cells(grid: Grid, refs: list[str]) -> list[str]:
    out: list[str] = []
    for ref in refs:
        cleaned = ref.strip().upper()
        if grid.contains(cleaned) and cleaned not in out:
            out.append(cleaned)
    return out
