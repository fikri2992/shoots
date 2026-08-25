"""The crop loop: the Composer's crop has to prove itself on the pixels.

The panel's Composer suggests ``suggested_crop_cells``. That is an opinion.
``refine()`` renders the crop, asks a rater to score the original and the
crop as finished frames, and keeps the crop only if the composition score
rose. If not, the rater may propose a better range; that gets one more
round. Bounded, deterministic, and the decision rests on a rendered image,
not on the Composer's description of one.

The loop is Python, not an ADK ``LoopAgent``, and that is a choice rather
than a constraint. ADK 2.7.1 does support ``output_schema`` together with
tools (``llm_agent.py``: tools are exposed during the thought loop and
structure is enforced only on the final output), so the old reason given
here was wrong. What remains true is that showing a rater a freshly rendered
image mid-invocation would need a ``before_model_callback``, and that path
is untested; this loop is bounded at two rounds, deterministic, and works.
``LoopAgent`` is also deprecated in 2.7.1.
"""

import logging
from dataclasses import dataclass

from google.adk.agents import LlmAgent
from PIL import Image
from pydantic import BaseModel, Field

from app.agents import prompts
from app.agents.runtime import bytes_part, run_agent
from app.config import settings
from app.domain import rubric
from app.domain.entities import Shot
from app.domain.grid import Grid
from app.imaging import canvas
from app.imaging.crop import crop_to_cells, is_sensible

logger = logging.getLogger(__name__)

MAX_ROUNDS = 2


class CropVerdict(BaseModel):
    composition_before: int = Field(ge=1, le=10)
    composition_after: int = Field(ge=1, le=10)
    keep: bool = False
    better_cells: list[str] = Field(default_factory=list)
    reason: str = ""


@dataclass
class CropResult:
    tested: bool
    kept: bool
    cells: list[str]
    before: int | None
    after: int | None
    rounds: int
    reason: str
    image: bytes | None  # the kept crop, JPEG


def crop_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="crop_rater",
        description="Scores a suggested crop against the original on the image.",
        instruction=prompts.load("crop"),
        output_schema=CropVerdict,
        output_key="crop",
    )


def prompt_for(shot: Shot, cells: list[str]) -> str:
    grid = shot.grid
    return (
        f"Grid: {grid.cols} columns x {grid.rows} rows "
        f"(cells A1 to {chr(ord('A') + grid.cols - 1)}{grid.rows}).\n"
        f"Image 1: the original frame with the grid. Image 2: the crop of cells {' '.join(cells)}."
    )


async def rate(shot: Shot, gridded: bytes, crop_jpeg: bytes, cells: list[str]) -> CropVerdict:
    return await run_agent(
        crop_agent(),
        prompt=prompt_for(shot, cells),
        images=[bytes_part(gridded, "image/png"), bytes_part(crop_jpeg, "image/jpeg")],
        schema=CropVerdict,
        user_id=shot.user_id,
        state={"anchors": rubric.anchors_text()},
    )


async def refine(
    shot: Shot, clean: Image.Image, gridded: bytes, cells: list[str], rounds: int = MAX_ROUNDS
) -> CropResult:
    """Test the Composer's crop, then at most one alternative. Never raises on
    a bad suggestion: an untested crop is reported as such."""
    grid = Grid(
        cols=shot.grid.cols, rows=shot.grid.rows, width=shot.grid.width, height=shot.grid.height
    )
    candidate = [c for c in cells if grid.contains(c)]
    before: int | None = None
    reason = ""
    tried = 0
    while candidate and tried < rounds and is_sensible(shot.grid, candidate):
        tried += 1
        cropped = crop_to_cells(clean, shot.grid, candidate)
        crop_jpeg = canvas.to_jpeg_bytes(canvas.fit_for_model(cropped))
        verdict = await rate(shot, gridded, crop_jpeg, candidate)
        before = verdict.composition_before if before is None else before
        reason = verdict.reason.strip()[:300]
        if verdict.keep and verdict.composition_after > verdict.composition_before:
            return CropResult(
                tested=True,
                kept=True,
                cells=candidate,
                before=before,
                after=verdict.composition_after,
                rounds=tried,
                reason=reason,
                image=crop_jpeg,
            )
        alternative = [c.strip().upper() for c in verdict.better_cells if grid.contains(c)]
        if not alternative or set(alternative) == set(candidate):
            break
        candidate = alternative
    return CropResult(
        tested=tried > 0,
        kept=False,
        cells=candidate,
        before=before,
        after=None,
        rounds=tried,
        reason=reason,
        image=None,
    )
