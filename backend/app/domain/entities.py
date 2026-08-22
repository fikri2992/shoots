"""The records Shoots keeps. Pydantic v2, stored as plain dicts in Firestore.

Vocabulary is docs/domain-model.md. A *shot* is one photo or video file. The
*Analyst* turns a shot into *evidence* for techniques. The *skill graph* is the
per-user state of every technique. A *quest* asks for one technique and says,
in machine-checkable terms, what counts as done.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# --- users ----------------------------------------------------------------


class DriveChannel(BaseModel):
    """A Drive push-notification channel. They expire; the Scheduler renews."""

    channel_id: str
    resource_id: str
    expires_at: datetime


class Constraints(BaseModel):
    """What the photographer told the Coach about their situation. The Scout
    respects it: no tripod techniques for someone with only a phone."""

    missing_gear: list[str] = Field(default_factory=list)  # tripod | telephoto | macro | flash
    notes: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None


class User(BaseModel):
    id: str
    email: str
    name: str = ""
    picture: str = ""
    constraints: Constraints = Field(default_factory=Constraints)
    drive_folder_id: str = ""
    drive_channel: DriveChannel | None = None
    #: Drive change-token cursor, so a notification costs one small list call.
    drive_page_token: str = ""
    drive_review_folder_id: str = ""
    #: Where they last shot, from the EXIF of their own frames (domain/timing.py).
    last_latitude: float | None = None
    last_longitude: float | None = None
    location_at: datetime | None = None
    created_at: datetime = Field(default_factory=now)


# --- shots ----------------------------------------------------------------


class ShotKind(StrEnum):
    PHOTO = "photo"
    VIDEO = "video"


class ShotStatus(StrEnum):
    NEW = "new"
    INGESTED = "ingested"
    ANALYZED = "analyzed"
    FAILED = "failed"


class Exif(BaseModel):
    """Hard evidence. Every field optional: phones and exports drop things."""

    make: str = ""
    model: str = ""
    lens: str = ""
    exposure_time_s: float | None = None
    f_number: float | None = None
    iso: int | None = None
    focal_length_mm: float | None = None
    focal_length_35mm: int | None = None
    flash_fired: bool | None = None
    captured_at: datetime | None = None
    #: From the GPS block when the camera wrote one. Feeds quest timing.
    latitude: float | None = None
    longitude: float | None = None


class VideoMeta(BaseModel):
    duration_s: float
    fps: float | None = None
    width: int
    height: int
    codec: str = ""
    lufs: float | None = None


class GridSpec(BaseModel):
    cols: int
    rows: int
    width: int
    height: int


class Shot(BaseModel):
    id: str
    user_id: str
    kind: ShotKind
    drive_file_id: str
    filename: str
    mime_type: str
    status: ShotStatus = ShotStatus.NEW
    exif: Exif = Field(default_factory=Exif)
    video: VideoMeta | None = None
    grid: GridSpec | None = None
    #: Blob paths by kind: original, gridded, contact_sheet, thumb.
    blobs: dict[str, str] = Field(default_factory=dict)
    #: Set when the user shot this for a specific quest.
    quest_id: str = ""
    #: The reviewed copy the Scribe wrote back into the user's Drive.
    drive_review_id: str = ""
    drive_review_url: str = ""
    error: str = ""
    captured_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=now)
    analyzed_at: datetime | None = None


# --- analysis -------------------------------------------------------------


class TechniqueEvidence(BaseModel):
    """One technique the Analyst believes this shot demonstrates."""

    technique_id: str
    confidence: float = Field(ge=0, le=1)
    #: Cells where the evidence is visible. Empty for global qualities.
    cells: list[str] = Field(default_factory=list)
    note: str = ""
    #: How many panel lenses saw it, and which (domain/panel.py).
    agreement: int = 1
    lenses: list[str] = Field(default_factory=list)


class Move(BaseModel):
    """A composition suggestion the dashboard draws as an arrow."""

    what: str
    from_cells: list[str]
    to_cells: list[str]
    reason: str


class Composition(BaseModel):
    subject_cells: list[str] = Field(default_factory=list)
    horizon_row: int | None = None
    suggested_crop_cells: list[str] = Field(default_factory=list)
    moves: list[Move] = Field(default_factory=list)


class Analysis(BaseModel):
    shot_id: str
    user_id: str
    model: str
    techniques: list[TechniqueEvidence] = Field(default_factory=list)
    composition: Composition = Field(default_factory=Composition)
    #: Neutral, cell-referenced description (Feldman's first step), before judgement.
    observations: list[str] = Field(default_factory=list)
    #: Rubric element scores 1-10 (domain/rubric.py), averaged over the lenses that rate each.
    elements: dict[str, int] = Field(default_factory=dict)
    critique: str = ""
    #: 1-10, computed from ``elements`` by the rubric's weights. Feeds best_score.
    score: int = Field(default=5, ge=1, le=10)
    #: Seconds each lens took; a lens missing here did not answer.
    panel: dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now)


# --- skill graph ----------------------------------------------------------


class SkillStatus(StrEnum):
    UNEXPLORED = "unexplored"
    ATTEMPTED = "attempted"  # seen once, low confidence or low score
    PRACTICED = "practiced"  # several shots, improving
    SOLID = "solid"  # consistently high score
    RUSTY = "rusty"  # was solid, not practiced for skill_decay_days


class SkillState(BaseModel):
    user_id: str
    technique_id: str
    status: SkillStatus = SkillStatus.UNEXPLORED
    attempts: int = 0
    best_score: int = 0
    last_score: int = 0
    last_practiced: datetime | None = None
    #: Shot ids, newest last, capped by the Cartographer.
    shot_ids: list[str] = Field(default_factory=list)


# --- quests ---------------------------------------------------------------


class ExifRule(BaseModel):
    """Machine-checkable criteria. None means "not constrained"."""

    shutter_max_s: float | None = None
    shutter_min_s: float | None = None
    aperture_max: float | None = None
    aperture_min: float | None = None
    iso_min: int | None = None
    iso_max: int | None = None
    focal_min_mm: int | None = None
    focal_max_mm: int | None = None
    flash: bool | None = None


class Criteria(BaseModel):
    exif: ExifRule = Field(default_factory=ExifRule)
    #: Technique ids the Analyst must see at >= judge_min_confidence.
    vision: list[str] = Field(default_factory=list)
    #: Plain-language version the user reads and the Judge quotes back.
    text: list[str] = Field(default_factory=list)


class Reference(BaseModel):
    title: str
    url: str


class QuestStatus(StrEnum):
    OPEN = "open"
    PASSED = "passed"
    SKIPPED = "skipped"  # the human gate: user declined it
    EXPIRED = "expired"


class Verdict(BaseModel):
    shot_id: str
    passed: bool
    exif_checks: dict[str, bool] = Field(default_factory=dict)
    vision_checks: dict[str, float] = Field(default_factory=dict)
    feedback: str
    judged_at: datetime = Field(default_factory=now)


class QuestTiming(BaseModel):
    """Why the quest lands when it does (domain/timing.py)."""

    light: str
    reason: str
    anchor: str = ""  # sunrise | sunset | dusk
    anchor_at: datetime | None = None


class Quest(BaseModel):
    id: str
    user_id: str
    technique_id: str
    title: str
    brief: str
    why_now: str  # the Scout's gap reasoning, shown to the user
    criteria: Criteria
    references: list[Reference] = Field(default_factory=list)
    reference_clip: str = ""  # blob path of the Veo clip
    #: When the push lands. The quest exists before that; the phone waits.
    deliver_at: datetime | None = None
    delivered_at: datetime | None = None
    timing: QuestTiming | None = None
    status: QuestStatus = QuestStatus.OPEN
    verdicts: list[Verdict] = Field(default_factory=list)
    issued_at: datetime = Field(default_factory=now)
    due_at: datetime | None = None
    closed_at: datetime | None = None


# --- audit trail ----------------------------------------------------------


class ActivityEvent(BaseModel):
    """Every agent step, durable. The live feed is a view of this."""

    id: str
    user_id: str
    agent: str  # ingest | analyst | cartographer | scout | judge | scheduler
    stage: str
    detail: dict = Field(default_factory=dict)
    shot_id: str = ""
    quest_id: str = ""
    at: datetime = Field(default_factory=now)
