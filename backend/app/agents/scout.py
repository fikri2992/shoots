"""The Scout's model half: research with Search grounding, then write the experiment.

Two calls on purpose, and not because ADK forbids one: 2.7.1 supports
``output_schema`` alongside tools. It is that only the grounded call's response
carries grounding metadata, and that metadata is where the real source URLs
live, so ``pick_references`` can never hand the photographer a URL a model
invented. Research is one grounded google-genai call; the experiment text comes
from an ADK agent against a schema, with the research handed to it as state.
Criteria never come from the model: they are the technique's EXIF bounds
plus its own id as the vision check (domain-model.md decision 4).
"""

import logging
import re
from dataclasses import dataclass, field

from google import genai
from google.adk.agents import LlmAgent
from google.genai import types
from pydantic import BaseModel, Field

from app.agents import prompts
from app.agents.retry import with_retry
from app.agents.runtime import run_agent
from app.config import settings
from app.domain.entities import Constraints, Criteria, ExifRule, Reference, TechniqueState
from app.domain.taxonomy import Technique

logger = logging.getLogger(__name__)


# --- research (grounded) --------------------------------------------------


@dataclass
class Research:
    notes: str
    references: list[Reference] = field(default_factory=list)


def research_prompt(technique: Technique) -> str:
    return (
        f"Research the photography technique '{technique.name}' "
        f"({technique.family.value}) for a beginner to intermediate photographer. "
        f"It is recognised by: {technique.cue}\n\n"
        "Find two or three well-regarded guides. Summarise in under 250 words: "
        "the camera settings that matter, where to stand and when, what the frame "
        "must show, and the most common mistake. Cite which source said what."
    )


async def research(technique: Technique) -> Research:
    client = genai.Client()

    async def attempt() -> Research:
        response = await client.aio.models.generate_content(
            model=settings.model_flash,
            contents=research_prompt(technique),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        notes = (response.text or "").strip()
        references = _references(response)
        return Research(notes=notes, references=references)

    return await with_retry(attempt)


def _references(response: types.GenerateContentResponse) -> list[Reference]:
    out: list[Reference] = []
    seen: set[str] = set()
    for candidate in response.candidates or []:
        meta = candidate.grounding_metadata
        for chunk in (meta.grounding_chunks if meta else None) or []:
            web = chunk.web
            if not web or not web.uri or web.uri in seen:
                continue
            seen.add(web.uri)
            out.append(Reference(title=(web.title or web.uri)[:120], url=web.uri))
    return out[:6]


# --- writing (structured) --------------------------------------------------


class ExperimentOut(BaseModel):
    title: str
    brief: str
    why_now: str = ""
    criteria_text: list[str] = Field(default_factory=list)
    reference_titles: list[str] = Field(default_factory=list)


def scout_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="scout",
        description="Writes one shootable experiment for a chosen technique from grounded notes.",
        instruction=prompts.load("scout"),
        output_schema=ExperimentOut,
        output_key="experiment",
    )


def criteria_for(technique: Technique, text: list[str]) -> Criteria:
    return Criteria(
        exif=ExifRule(**technique.exif),
        vision=[technique.id],
        text=[t.strip() for t in text if t.strip()][:4],
    )


def hard_criteria_text(technique: Technique) -> str:
    rule = technique.exif
    parts = []
    if "shutter_min_s" in rule:
        parts.append(f"shutter at least {_shutter(rule['shutter_min_s'])}")
    if "shutter_max_s" in rule:
        parts.append(f"shutter no slower than {_shutter(rule['shutter_max_s'])}")
    if "aperture_max" in rule:
        parts.append(f"aperture f/{rule['aperture_max']:g} or wider")
    if "aperture_min" in rule:
        parts.append(f"aperture f/{rule['aperture_min']:g} or narrower")
    if "iso_min" in rule:
        parts.append(f"ISO {rule['iso_min']} or higher")
    if "iso_max" in rule:
        parts.append(f"ISO {rule['iso_max']} or lower")
    if "focal_min_mm" in rule:
        parts.append(f"focal length {rule['focal_min_mm']} mm or longer (35 mm equivalent)")
    if "focal_max_mm" in rule:
        parts.append(f"focal length {rule['focal_max_mm']} mm or shorter (35 mm equivalent)")
    if "flash" in rule:
        parts.append("flash must fire" if rule["flash"] else "no flash")
    return "; ".join(parts) if parts else "none (judged on the frame alone)"


def _shutter(seconds: float) -> str:
    return f"{seconds:g} s" if seconds >= 1 else f"1/{round(1 / seconds)} s"


def write_prompt(
    technique: Technique,
    why: str,
    critiques: list[str],
    notes: Research,
    skills: dict[str, TechniqueState],
    constraints: Constraints | None = None,
) -> str:
    recent = "\n".join(f"- {c}" for c in critiques[:5]) or "- none yet"
    refs = "\n".join(f"- {r.title}: {r.url}" for r in notes.references) or "- none"
    said: list[str] = []
    if constraints and constraints.missing_gear:
        said.append(f"- Has no {', '.join(constraints.missing_gear)}.")
    if constraints:
        said += [f"- {n}" for n in constraints.notes]
    told = "\n".join(said) or "- nothing yet"
    return (
        f"Technique: `{technique.id}` — {technique.name} ({technique.family.value}, "
        f"level {technique.level}).\nRecognised by: {technique.cue}\n"
        f"Hard criteria (fixed): {hard_criteria_text(technique)}\n"
        f"Why now: {why}\n"
        f"Techniques the photographer has attempted so far: "
        f"{', '.join(sorted(skills)) or 'none'}\n\n"
        f"What the photographer has told the Coach about their situation:\n{told}\n\n"
        f"Recent critiques of their shots:\n{recent}\n\n"
        f"Research notes:\n{notes.notes or '(no notes; rely on common practice)'}\n\n"
        f"Sources:\n{refs}"
    )


async def write(
    technique: Technique,
    why: str,
    critiques: list[str],
    notes: Research,
    skills: dict[str, TechniqueState],
    constraints: Constraints | None = None,
) -> ExperimentOut:
    return await run_agent(
        scout_agent(),
        prompt=write_prompt(technique, why, critiques, notes, skills, constraints),
        schema=ExperimentOut,
    )


_INLINE_STEP = re.compile(r"\s+(?=\d{1,2}[.)]\s)")


def normalise_brief(brief: str) -> str:
    """One numbered step per line. The model sometimes runs "1. … 2. …"
    together on one line; the card and the Judge both read it line by line."""
    text = " ".join(brief.split())
    if "\n" in brief.strip():
        lines = [" ".join(line.split()) for line in brief.strip().splitlines()]
        return "\n".join(line for line in lines if line)
    parts = [p.strip() for p in _INLINE_STEP.split(text) if p.strip()]
    return "\n".join(parts)


def pick_references(out: ExperimentOut, research: Research) -> list[Reference]:
    """Only URLs the grounded call actually returned; titles are the model's pick."""
    wanted = [t.strip().lower() for t in out.reference_titles]
    chosen = [r for r in research.references if r.title.strip().lower() in wanted]
    return (chosen or research.references)[:3]
