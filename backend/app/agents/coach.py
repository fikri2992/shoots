"""The Coach: a Gemini Live voice session about one shot.

The phone streams microphone PCM to ``api/live.py``, which relays it into a
Live session opened here; the model's audio and transcripts go back the
same way. This module owns the session config, the briefing the model gets
before the first word, and the translation of Live server messages into the
small set of events the socket forwards. The translation is pure and tested;
the session itself is checked by ``scripts/check_coach.py``.
"""

from dataclasses import dataclass, field

from google import genai
from google.adk.agents import LlmAgent
from google.genai import types
from pydantic import BaseModel, Field

from app.agents import prompts
from app.agents.analyst import facts_text
from app.agents.runtime import run_agent
from app.config import settings
from app.domain import taxonomy
from app.domain.entities import Analysis, Constraints, Experiment, PhotographerSignalKind, Shot

#: What the browser sends us and what Live expects: 16 kHz mono PCM16.
INPUT_MIME = "audio/pcm;rate=16000"
#: What Live sends back. The browser's player is built for this rate.
OUTPUT_RATE = 24000


@dataclass
class Event:
    kind: str  # audio | transcript | interrupted | turn_complete | tool_call
    data: bytes = b""
    role: str = ""  # transcript only: user | model
    text: str = ""
    #: tool_call only: the model's function calls, in order.
    calls: list = field(default_factory=list)


def briefing(
    shot: Shot,
    analysis: Analysis | None,
    experiment: Experiment | None,
    constraints: Constraints | None = None,
) -> str:
    """Everything the Coach knows about the Shot before the first word."""
    grid = shot.grid
    lines = [
        f"Grid: {grid.cols} columns x {grid.rows} rows "
        f"(cells A1 to {chr(ord('A') + grid.cols - 1)}{grid.rows}).",
        f"Shot kind: {'video contact sheet' if shot.kind.value == 'video' else 'photo'}.",
        f"File: {shot.filename}",
        "",
        "Camera facts:",
        facts_text(shot.exif, shot.video),
        "",
    ]
    if analysis:
        seen = (
            "\n".join(
                f"- {t.technique_id} ({t.confidence:.0%}) at {' '.join(t.cells) or '?'}: {t.note}"
                for t in analysis.techniques
            )
            or "- nothing tagged with confidence"
        )
        comp = analysis.composition
        moves = (
            "\n".join(
                f"- {m.what}: {','.join(m.from_cells)} -> {','.join(m.to_cells)} ({m.reason})"
                for m in comp.moves
            )
            or "- none"
        )
        lines += [
            "Analyst's read:",
            f"Techniques seen:\n{seen}",
            f"Subject cells: {' '.join(comp.subject_cells) or '?'}",
            f"Horizon row: {comp.horizon_row if comp.horizon_row is not None else 'none'}",
            f"Suggested crop: {' '.join(comp.suggested_crop_cells) or 'none'}",
            f"Suggested moves:\n{moves}",
            f"Critique: {analysis.critique}",
            "",
        ]
    else:
        lines += ["The Analyst has not read this Shot yet; work from the image alone.", ""]
    if experiment:
        lines += [
            f"This Shot was made for the Experiment '{experiment.title}' "
            f"(technique {experiment.technique_id}, status {experiment.status.value}).",
            "Criteria: " + "; ".join(experiment.criteria.text),
            "",
        ]
    if constraints and (constraints.missing_gear or constraints.notes):
        lines.append("What the photographer has told you before (do not ask again):")
        if constraints.missing_gear:
            lines.append(f"- No {', '.join(constraints.missing_gear)}.")
        lines += [f"- {note}" for note in constraints.notes]
        lines.append("")
    lines.append(
        "Technique ids you may pass to issue_experiment (only these): "
        + ", ".join(t.id for t in taxonomy.TECHNIQUES if not t.video_only)
    )
    lines.append("Begin the session as instructed.")
    return "\n".join(lines)


# --- after the session: what to remember --------------------------------------


class ListenerFactOut(BaseModel):
    kind: PhotographerSignalKind = PhotographerSignalKind.CONSTRAINT
    value: str
    quote: str


class NotesOut(BaseModel):
    facts: list[ListenerFactOut] = Field(default_factory=list)


def listener_agent() -> LlmAgent:
    return LlmAgent(
        model=settings.model_flash,
        name="listener",
        description="Extracts standing constraints from a coaching transcript.",
        instruction=prompts.load("listener"),
        output_schema=NotesOut,
        output_key="notes",
    )


def transcript_text(transcript: list[dict]) -> str:
    return "\n".join(
        f"{'Photographer' if t['role'] == 'user' else 'Coach'}: {t['text'].strip()}"
        for t in transcript
        if t["text"].strip()
    )


async def listen(transcript: list[dict], user_id: str) -> NotesOut:
    return await run_agent(
        listener_agent(),
        prompt="Transcript:\n" + transcript_text(transcript)[-6000:],
        schema=NotesOut,
        user_id=user_id,
    )


TOOLS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="issue_experiment",
            description=(
                "Issue the photographer a new experiment for a technique right now, replacing the "
                "open one. Use when they ask for something else to shoot. Pass a technique id "
                "from the list you were given; omit it to let the Scout choose."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "technique_id": types.Schema(type=types.Type.STRING),
                    "reason": types.Schema(
                        type=types.Type.STRING, description="One sentence: why this, here, now."
                    ),
                },
            ),
        ),
        types.FunctionDeclaration(
            name="remember",
            description=(
                "Remember a standing fact about the photographer that should change "
                "future experiments: gear they lack (tripod, telephoto, macro, flash) "
                "or when and where they shoot."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "missing_gear": types.Schema(
                        type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)
                    ),
                    "notes": types.Schema(
                        type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)
                    ),
                    "statement": types.Schema(
                        type=types.Type.STRING,
                        description="The photographer's exact words supporting these facts.",
                    ),
                },
                required=["statement"],
            ),
        ),
        types.FunctionDeclaration(
            name="technique_map",
            description=(
                "The photographer's Technique Map: what the Evidence has observed and what "
                "recurs. States are unobserved, observed and "
                "recurring - they describe the evidence, never the photographer's ability."
            ),
            parameters=types.Schema(type=types.Type.OBJECT, properties={}),
        ),
    ]
)


def live_config() -> types.LiveConnectConfig:
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        tools=[TOOLS],
        system_instruction=prompts.load("coach"),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=settings.live_voice)
            )
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )


def connect():
    """Async context manager yielding a Live session. Vertex, us-central1."""
    client = genai.Client(
        vertexai=True, project=settings.gcp_project, location=settings.live_location
    )
    return client.aio.live.connect(model=settings.model_live, config=live_config())


def opening_turn(image: bytes, mime_type: str, text: str) -> types.Content:
    return types.Content(
        role="user",
        parts=[types.Part.from_bytes(data=image, mime_type=mime_type), types.Part(text=text)],
    )


def events_from(message: types.LiveServerMessage) -> list[Event]:
    """The few things the phone cares about, in arrival order."""
    if message.tool_call and message.tool_call.function_calls:
        return [Event("tool_call", calls=list(message.tool_call.function_calls))]
    content = message.server_content
    if content is None:
        return []
    events: list[Event] = []
    if content.interrupted:
        events.append(Event("interrupted"))
    if content.model_turn:
        for part in content.model_turn.parts or []:
            blob = part.inline_data
            if blob and blob.data and (blob.mime_type or "").startswith("audio/"):
                events.append(Event("audio", data=blob.data))
    if content.input_transcription and content.input_transcription.text:
        events.append(Event("transcript", role="user", text=content.input_transcription.text))
    if content.output_transcription and content.output_transcription.text:
        events.append(Event("transcript", role="model", text=content.output_transcription.text))
    if content.turn_complete:
        events.append(Event("turn_complete"))
    return events
