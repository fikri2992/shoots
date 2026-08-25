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


class Tone(BaseModel):
    """What the pixels say about colour and tone (``imaging/tone.py``).

    Exif for everything the camera did not write down. Every real file in the
    corpus reports ``WhiteBalance: 0`` — auto — and ``LightSource: 255`` —
    other, so the camera records that it decided and not what it decided.
    Colour therefore has to be measured off the frame or it is not evidence at
    all, which is what left the colour and light families making claims with
    nothing behind them while composition had a grid, a guide and four faults.

    Raw measurements only, like ``Exif``. ``domain/tone.py`` does the arithmetic
    on top, the same way ``domain/exposure.py`` sits on ``Exif``.
    """

    #: Correlated colour temperature by McCamy's approximation, from the frame's
    #: mean chromaticity. Daylight is ~5500 K; tungsten ~3200 K; open shade ~8000 K.
    cct_k: int | None = None
    #: Mean red minus mean blue, 0-255 scale. Positive is a warm cast.
    cast: float = 0.0
    #: Mean HSV saturation, as a percentage of full.
    saturation: float = 0.0
    #: The 95th percentile of saturation: how loud the loudest colour gets. A
    #: single accent is a low mean with a high p95 over a small share.
    saturation_p95: float = 0.0
    #: Share of the frame that is strongly saturated.
    accent_share: float = 0.0
    #: Shares of the frame reading warm and cool by hue, ignoring near-greys.
    warm_share: float = 0.0
    cool_share: float = 0.0
    #: Luminance, 0-255. The percentiles rather than the extremes, so one
    #: specular highlight cannot describe the frame.
    luma_mean: float = 0.0
    luma_p5: float = 0.0
    luma_p95: float = 0.0
    #: Percentage of the frame at the ends of the scale, where detail is gone.
    clipped_high: float = 0.0
    clipped_low: float = 0.0
    #: The dominant hue families, most common first, and the angle between the
    #: top two in degrees. Near 180 is complementary; under 45 is analogous.
    hues: list[str] = Field(default_factory=list)
    hue_opposition: int | None = None


class Motion(BaseModel):
    """How the camera itself moved, measured between frames (``imaging/motion.py``).

    Camera-move techniques were being read off a contact sheet of scene-cut
    stills, which cannot separate a pan from a tracking shot from a push in:
    twelve video techniques were firing at 0.11 per shot against composition's
    1.94. The frames hold the answer, but only consecutive ones do, so this is
    measured on a dense low-resolution strip rather than on the sheet.

    Displacements are signed and in frame widths, so they mean the same thing
    at any resolution: ``drift_x`` of 2.4 is a pan across two and a half frames.
    """

    #: Samples compared, and the rate they were taken at.
    frames: int = 0
    fps: float = 0.0
    #: Cumulative displacement over the clip, in frame widths and heights.
    #: Positive ``drift_x`` means the framing travelled right.
    drift_x: float = 0.0
    drift_y: float = 0.0
    #: Mean and largest single-step displacement, in frame widths. A whip pan
    #: is not a fast pan: it is one step large enough to smear.
    step: float = 0.0
    step_max: float = 0.0
    #: How often the horizontal direction reversed. A pan holds its direction;
    #: handheld wobble does not.
    reversals: int = 0
    #: Share of steps where the framing did not move at all.
    still_share: float = 0.0


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
    #: Measured off the frame at ingest, beside the EXIF the camera wrote.
    tone: Tone = Field(default_factory=Tone)
    #: Video only: how the camera moved. None on a photo and on a clip too
    #: short to compare two frames.
    motion: Motion | None = None
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


class Fault(BaseModel):
    """Something wrong with a frame, decided by arithmetic (``domain/faults.py``).

    The mirror of ``TechniqueEvidence``: that says what the frame achieved and
    carries a confidence because a model saw it; this says what the frame gets
    wrong and carries a figure because code computed it. No confidence field —
    a fault the numbers cannot settle is never raised.
    """

    fault_id: str
    #: The fault in the photographer's words. Reads on its own.
    what: str
    #: The arithmetic behind it. Never empty: a fault without a figure is an
    #: opinion, and opinions belong to the lenses.
    why: str
    cells: list[str] = Field(default_factory=list)


class MoveKind(StrEnum):
    """What kind of change is being asked for, which decides how it is drawn.

    A crop is not a translation and a camera position is not a 2D vector;
    drawing either as an arrow is what made the overlay nonsense.
    """

    MOVE = "move"  # reposition something inside the frame: an arrow
    CROP = "crop"  # take an edge away: a dimmed region, never an arrow
    CAMERA = "camera"  # stand somewhere else: words, no mark on the frame


class Move(BaseModel):
    """One concrete change to the frame."""

    what: str
    kind: MoveKind = MoveKind.MOVE
    from_cells: list[str] = Field(default_factory=list)
    to_cells: list[str] = Field(default_factory=list)
    reason: str = ""


class Composition(BaseModel):
    subject_cells: list[str] = Field(default_factory=list)
    #: The subject's centre in frame units (0-1), when the Composer gave one
    #: that falls inside ``subject_cells``. Cells quantise to a seventh of the
    #: width; a guide that measures against a thirds line needs finer than that.
    subject_x: float | None = None
    subject_y: float | None = None
    #: Which compositional guide a human should see over this frame
    #: (``domain/guides.py``), chosen from the techniques the panel agreed on.
    guide: str = ""
    horizon_row: int | None = None
    #: After the crop loop: only a crop that scored higher on the rendered
    #: image survives here (agents/crop.py). An untested suggestion is cleared.
    suggested_crop_cells: list[str] = Field(default_factory=list)
    crop_tested: bool = False
    crop_before: int | None = None
    crop_after: int | None = None
    crop_rounds: int = 0
    crop_reason: str = ""
    moves: list[Move] = Field(default_factory=list)


class Analysis(BaseModel):
    shot_id: str
    user_id: str
    model: str
    techniques: list[TechniqueEvidence] = Field(default_factory=list)
    composition: Composition = Field(default_factory=Composition)
    #: Neutral, cell-referenced description (Feldman's first step), before judgement.
    observations: list[str] = Field(default_factory=list)
    #: What the arithmetic says is wrong with the frame (domain/faults.py).
    #: Computed after the vote, so a technique can excuse its own side effect.
    faults: list[Fault] = Field(default_factory=list)
    #: Rubric element scores 1-10 (domain/rubric.py), averaged over the lenses that rate each.
    elements: dict[str, int] = Field(default_factory=dict)
    critique: str = ""
    #: 1-10, computed from ``elements`` by the rubric's weights. Feeds best_score.
    score: int = Field(default=5, ge=1, le=10)
    #: Seconds each lens took; a lens missing here did not answer.
    panel: dict[str, float] = Field(default_factory=dict)
    #: Sightings that lost the vote: [{lens, technique_id, confidence}]. Shown, not counted.
    dissent: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now)


# --- skill graph ----------------------------------------------------------


class SkillStatus(StrEnum):
    UNEXPLORED = "unexplored"
    ATTEMPTED = "attempted"  # seen, but by one lens or without conviction
    PRACTICED = "practiced"  # seen again, and corroborated at least once
    SOLID = "solid"  # corroborated by two lenses, three times over
    RUSTY = "rusty"  # was solid, not practiced for skill_decay_days


class SkillState(BaseModel):
    """What the map knows about one technique for one photographer.

    ``corroborated`` is what moves the status, not ``best_score``. The score
    belongs to the whole frame: one photograph demonstrating six techniques
    hands the same number to all six, so promoting on it credits every
    technique in the frame for whatever the best one earned. Agreement and
    confidence are the only signals that are *about this technique*.
    """

    user_id: str
    technique_id: str
    status: SkillStatus = SkillStatus.UNEXPLORED
    attempts: int = 0
    #: Attempts where more than one lens saw it and both were sure.
    corroborated: int = 0
    #: Highest voted confidence this technique has ever reached.
    best_confidence: float = 0.0
    #: The frame's overall score when this technique was last seen, and the
    #: best such frame. Recorded for the Judge's comparison and the Coach's
    #: briefing; deliberately not part of the promotion rule.
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
    #: The user's previous best shot for the technique the feedback compared against.
    compared_with: str = ""
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
