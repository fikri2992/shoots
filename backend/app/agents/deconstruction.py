"""One bounded story-writing step inside Scribe, never a new Analyst run."""

import asyncio
import json
from typing import Literal

from google.adk.agents import LlmAgent
from pydantic import Field, create_model

from app.agents import prompts
from app.agents.runtime import bytes_part, run_agent
from app.config import settings
from app.domain.entities import DeconstructionBeat, DeconstructionEvidence, DeconstructionStory


def _output_schema(evidence: list[DeconstructionEvidence]) -> type[DeconstructionStory]:
    """Constrain the writer to the exact visual choices it can actually see."""
    reference = Literal[tuple(item.id for item in evidence)]
    # Vertex's enum schema rejects empty strings. The wire sentinel is mapped
    # back to the existing empty selection only after validating the response.
    detail = Literal[tuple(["none", *(item.id for item in evidence if item.cells)])]
    artifact = Literal[
        tuple(
            [
                "none",
                *(item.id for item in evidence if item.visual_artifact and item.artifact_sha256),
            ]
        )
    ]
    beat = create_model(
        "DeconstructionVisualBeat",
        __base__=DeconstructionBeat,
        evidence_ids=(list[reference], Field(min_length=1)),
        detail_evidence_id=(detail, Field(default="none")),
        artifact_evidence_id=(artifact, Field(default="none")),
    )
    opening = create_model(
        "DeconstructionCleanOpening",
        __base__=beat,
        detail_evidence_id=(Literal["none"], "none"),
        artifact_evidence_id=(Literal["none"], "none"),
    )
    return create_model(
        "DeconstructionVisualStory",
        __base__=DeconstructionStory,
        opening=(opening | None, None),
        beats=(list[beat], Field(default_factory=list)),
        caption_evidence_ids=(list[reference], Field(default_factory=list)),
    )


async def write(
    user_id: str,
    evidence: list[DeconstructionEvidence],
    image: bytes,
    detail_sheet: bytes | None = None,
    artifact_sheet: bytes | None = None,
) -> DeconstructionStory:
    schema = _output_schema(evidence)
    agent = LlmAgent(
        model=settings.model_flash,
        name="deconstruction_writer",
        description="Writes a selected Shot's social carousel from its stored visual Evidence.",
        instruction=prompts.load("deconstruction"),
        output_schema=schema,
        output_key="deconstruction_story",
    )
    async with asyncio.timeout(settings.deconstruction_timeout_seconds):
        result = await run_agent(
            agent,
            schema=schema,
            user_id=user_id,
            prompt="Write a visual story for the supplied Shot. Return the structured draft.",
            images=[bytes_part(image, "image/jpeg")]
            + ([bytes_part(artifact_sheet, "image/jpeg")] if artifact_sheet else [])
            + ([bytes_part(detail_sheet, "image/jpeg")] if detail_sheet else []),
            state={
                "evidence": json.dumps(
                    [
                        item.model_dump(
                            mode="json",
                            exclude={
                                "artifact_sha256": True,
                                "visual_artifact": {
                                    "blob_path",
                                    "source_digest",
                                    "renderer_version",
                                },
                            },
                        )
                        for item in evidence
                    ]
                ),
                "max_beats": str(settings.deconstruction_max_story_pages),
            },
        )
    data = result.model_dump()
    for beat in ([data["opening"]] if data["opening"] else []) + data["beats"]:
        for field in ("detail_evidence_id", "artifact_evidence_id"):
            if beat[field] == "none":
                beat[field] = ""
    return DeconstructionStory.model_validate(data)
