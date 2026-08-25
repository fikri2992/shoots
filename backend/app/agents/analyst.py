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
from typing import Literal

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.genai import types
from pydantic import BaseModel, Field

from app.agents import prompts
from app.agents.runtime import WorkflowResult, bytes_part, run_workflow
from app.config import settings
from app.domain import exposure, faults, guides, motion, panel, rubric, taxonomy, tone
from app.domain.entities import (
    Analysis,
    Composition,
    Exif,
    Move,
    MoveKind,
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
    #: Required, and an enum: how the change is drawn depends entirely on it,
    #: and an optional field is too easily skipped.
    kind: Literal["move", "crop", "camera"]
    from_cells: list[str] = Field(default_factory=list)
    to_cells: list[str] = Field(default_factory=list)
    reason: str = ""


class CompositionOut(BaseModel):
    subject_cells: list[str] = Field(default_factory=list)
    #: The subject's centre in frame units, finer than the cell grid can say.
    subject_x: float
    subject_y: float
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

#: Which image each reader is left with, by position in the list ``analyse``
#: sends: 0 is the gridded frame, 1 is the clean one, and ``None`` is no image
#: at all. Decision 18 has always said the lenses differ in instruction *and*
#: input, but the panel is a ParallelAgent under one user turn, so every lens
#: saw both frames and the input half was only ever prose inside the prompts.
#: The Storyteller in particular is asked what the picture feels like while
#: looking at a mesh drawn over it, and the Synthesizer, which is documented as
#: never seeing the image, saw two.
SEES: dict[str, int | None] = {
    panel.TECHNICIAN: 0,
    panel.COMPOSER: 0,
    panel.STORYTELLER: 1,
    "synthesizer": None,
}


def only_image(contents: list[types.Content], keep: int | None) -> list[types.Content]:
    """The same conversation with every image dropped except the ``keep``-th,
    counting images in the order they were sent. ``None`` drops all of them.
    Pure, so the routing can be tested without a model."""
    out: list[types.Content] = []
    seen = -1
    for content in contents:
        parts = []
        for part in content.parts or []:
            if getattr(part, "inline_data", None) is not None:
                seen += 1
                if keep is None or seen != keep:
                    continue
            parts.append(part)
        out.append(types.Content(role=content.role, parts=parts))
    return out


def _sees(keep: int | None):
    """A ``before_model_callback`` leaving this reader only its own frame.
    ADK builds one request per sub-agent from the shared session, so this is
    the seam where a ParallelAgent's readers stop sharing their eyes."""

    def callback(callback_context, llm_request):  # noqa: ANN001 — ADK's signature
        llm_request.contents = only_image(list(llm_request.contents or []), keep)
        return None

    return callback


def lens_agent(name: str) -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name=name,
        description=f"The {name} lens of the Analyst panel.",
        instruction=prompts.load(name),
        output_schema=SCHEMAS[name],
        output_key=name,
        before_model_callback=_sees(SEES[name]),
    )


def synthesizer_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="synthesizer",
        description="Writes the critique from the three lenses' readings.",
        instruction=prompts.load("synthesizer"),
        output_schema=SynthesisOut,
        output_key="synthesis",
        before_model_callback=_sees(SEES["synthesizer"]),
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


def _bullets(lines: list[str], empty: str) -> str:
    return "\n".join(f"- {line}" for line in lines) if lines else f"- {empty}"


def state_for(shot: Shot) -> dict[str, str]:
    """Session state the instructions template from.

    Measurements are routed to the lens that owns the family they speak to
    (``panel.OWNER_BY_FAMILY``) and to no other: the Technician gets the
    exposure and where the scale ran out, the Composer the temperature and the
    key, the Storyteller the palette. Handing all three the same numbers would
    buy anchored claims at the cost of the thing the panel exists for — three
    readings whose errors are not shared — so the facts are disjoint, exactly
    as the images already are.
    """
    camera = facts_text(shot.exif, shot.video)
    moves = motion.describe(shot.motion)
    # The Synthesizer is the one reader that gets all of it: it writes the only
    # paragraph the photographer is guaranteed to read, and a paragraph that
    # cannot cite the arithmetic is a paragraph any model could have written
    # from the picture alone.
    measured = [*exposure.describe(shot.exif), *tone.describe(shot.tone, shot.exif), *moves]
    return {
        "facts": camera + "\n" + _bullets(tone.technical(shot.tone), "tone not measured"),
        "light": _bullets(tone.light(shot.tone, shot.exif), "light not measured"),
        "palette": _bullets(tone.palette(shot.tone), "colour not measured"),
        "camera_move": _bullets(moves, "not a video, or the camera move was not measurable"),
        "measured": _bullets(measured, "nothing could be measured on this file"),
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
    # The measured camera move is not advice here, it is a vote. What the drift
    # rules out loses its evidence whatever a lens claimed; what the drift
    # settles needs only one lens to have noticed (domain/panel.py).
    travelled = motion.read(shot.motion)
    consensus = panel.aggregate(
        reads,
        min_confidence=settings.panel_min_confidence,
        min_agreement=settings.panel_min_agreement,
        owner_confidence=settings.panel_owner_confidence,
        quorum=settings.panel_quorum,
        settled_for=travelled.supports,
        settled_against=travelled.contradicts,
    )
    for lens, tid, confidence in consensus.dissent:
        logger.info(
            "panel: %s alone saw %s at %.2f on %s; not counted", lens, tid, confidence, shot.id
        )

    composer = result.reads.get(panel.COMPOSER)
    raw_comp = (
        composer.composition
        if isinstance(composer, ComposerOut)
        else CompositionOut(subject_x=0.5, subject_y=0.5)
    )
    moves = _moves(grid, raw_comp)
    # A crop asked for as a move is still a crop: send it to the crop loop,
    # where it has to beat the original on the pixels before anyone sees it.
    crop = _cells(grid, raw_comp.suggested_crop_cells) or next(
        (m.to_cells for m in moves if m.kind is MoveKind.CROP and m.to_cells), []
    )
    subject_cells = _cells(grid, raw_comp.subject_cells)
    point = _subject_point(grid, raw_comp, subject_cells)
    horizon = raw_comp.horizon_row
    if horizon is not None and not (1 <= horizon <= grid.rows):
        horizon = None

    critique = (result.synthesis.critique if result.synthesis else "").strip()
    if not critique:
        critique = " ".join(r.note.strip() for r in result.reads.values() if r.note.strip())

    # After the vote, so a technique can excuse the side effect it asks for: a
    # two-second light trail is not camera shake.
    found = faults.detect(
        exif=shot.exif,
        grid=grid,
        technique_ids=[t.technique_id for t in consensus.techniques],
        subject_cells=subject_cells,
        subject_x=point[0],
        subject_y=point[1],
        horizon_row=horizon,
        tone=shot.tone,
    )
    for fault in found:
        logger.info("faults: %s on %s (%s)", fault.fault_id, shot.id, fault.why)

    return Analysis(
        shot_id=shot.id,
        user_id=shot.user_id,
        model=settings.model_flash,
        techniques=consensus.techniques,
        composition=Composition(
            subject_cells=subject_cells,
            subject_x=point[0],
            subject_y=point[1],
            guide=guides.choose(consensus.techniques, point[0], point[1]),
            horizon_row=horizon,
            suggested_crop_cells=crop,
            moves=moves,
        ),
        faults=found,
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


def _moves(grid: Grid, raw: CompositionOut) -> list[Move]:
    """Keep only the changes that can be drawn as what they are.

    An arrow is a repositioning inside the frame and needs both ends. A crop
    only needs the region that survives. A camera change is words: it has no
    honest mark on a flat image, so its cells are dropped.
    """
    out: list[Move] = []
    for raw_move in raw.moves[:3]:
        what = raw_move.what.strip()[:80]
        if not what:
            continue
        kind = MoveKind(raw_move.kind)
        move = Move(
            what=what,
            kind=kind,
            from_cells=_cells(grid, raw_move.from_cells),
            to_cells=_cells(grid, raw_move.to_cells),
            reason=raw_move.reason.strip()[:300],
        )
        if kind is MoveKind.CAMERA:
            move.from_cells = []
            move.to_cells = []
        elif kind is MoveKind.CROP:
            move.from_cells = []
            if not move.to_cells:
                continue
        elif not (move.from_cells and move.to_cells):
            continue
        out.append(move)
    return out


def _subject_point(
    grid: Grid, raw: CompositionOut, subject_cells: list[str]
) -> tuple[float | None, float | None]:
    """The subject's centre in frame units, kept only if it agrees with the
    cells the same lens named. A point that contradicts them is a guess."""
    x, y = raw.subject_x, raw.subject_y
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        return None, None
    if not subject_cells:
        return round(x, 4), round(y, 4)
    box = grid.span_bounds(subject_cells)
    inside = (
        box.left / grid.width <= x <= box.right / grid.width
        and box.top / grid.height <= y <= box.bottom / grid.height
    )
    return (round(x, 4), round(y, 4)) if inside else (None, None)


def _cells(grid: Grid, refs: list[str]) -> list[str]:
    out: list[str] = []
    for ref in refs:
        cleaned = ref.strip().upper()
        if grid.contains(cleaned) and cleaned not in out:
            out.append(cleaned)
    return out
