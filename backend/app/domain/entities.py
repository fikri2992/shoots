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
    #: The panel is running right now. Written before the first model call so
    #: a redelivery mid-flight skips instead of re-paying for four to six of
    #: them; ``analysing_at`` dates the claim so a dead attempt cannot strand
    #: the shot here (see ``services/analyst.py``).
    ANALYSING = "analysing"
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
    nothing behind them while composition had a grid, a guide and four findings.

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
    #: When the photographer marked this Shot as one they value, or None.
    #:
    #: Positive only, and the distinction is the whole point (decision 45).
    #: ``kept_at`` set means *valued*. ``None`` means *unknown* - the
    #: photographer said nothing about this frame - and never *rejected*. A
    #: hobbyist marks a handful of frames and ignores the rest, so treating
    #: silence as dislike would invent a negative verdict they never gave and
    #: quietly make the model's taste into theirs.
    #:
    #: Unmarking returns a Shot to unknown rather than recording a rejection.
    #: An explicit "not for me" signal would be a separate concept and does not
    #: exist. This is the only source of taste in the system: it separates "you
    #: do this often", which the Tendency Profile measures on its own, from
    #: "this is what you value", which nothing else can supply. It is not a
    #: score, it promotes nothing, and it is never second-guessed.
    kept_at: datetime | None = None
    #: The camera's pitch when the shutter fired, degrees from level: negative
    #: is aimed down, positive up. Only shots taken through the Shoots camera
    #: carry it, which is why height is a declared blind spot of the profile.
    pitch_deg: float | None = None
    #: The reviewed copy the Scribe wrote back into the user's Drive.
    drive_review_id: str = ""
    drive_review_url: str = ""
    error: str = ""
    captured_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=now)
    #: When the panel claimed this shot. Read only while the status is
    #: ANALYSING, to tell an attempt in flight from one that died.
    analysing_at: datetime | None = None
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


class Finding(BaseModel):
    """Something wrong with a frame, decided by arithmetic (``domain/findings.py``).

    The mirror of ``TechniqueEvidence``: that says what the frame achieved and
    carries a confidence because a model saw it; this says what the frame gets
    wrong and carries a figure because code computed it. No confidence field —
    a finding the numbers cannot settle is never raised.
    """

    finding_id: str
    #: The finding in the photographer's words. Reads on its own.
    what: str
    #: The arithmetic behind it. Never empty: a finding without a figure is an
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
    #: What the arithmetic says is wrong with the frame (domain/findings.py).
    #: Computed after the vote, so a technique can excuse its own side effect.
    findings: list[Finding] = Field(default_factory=list)
    #: Rubric element scores 1-10 (domain/rubric.py), averaged over the lenses that rate each.
    elements: dict[str, int] = Field(default_factory=dict)
    critique: str = ""
    #: 1-10, computed from ``elements`` by the rubric's weights. Feeds best_score.
    score: int = Field(default=5, ge=1, le=10)
    #: Seconds each lens took; a lens missing here did not answer.
    panel: dict[str, float] = Field(default_factory=dict)
    #: Sightings that lost the vote: [{lens, technique_id, confidence}]. Shown, not counted.
    dissent: list[dict] = Field(default_factory=list)
    #: Set when the panel could not call this frame: every lens saw something
    #: and no two saw the same thing (decision 38). The findings still stand -
    #: they are arithmetic - but nothing here should be read as a verdict, and
    #: the review says so rather than averaging three opinions into one.
    abstained: str = ""
    created_at: datetime = Field(default_factory=now)


# --- skill graph ----------------------------------------------------------


class TechniqueStatus(StrEnum):
    """What the record has observed about one Technique (decision 46).

    Three states, and all three are statements about *the evidence*, never
    about the photographer's ability. `solid`, `practiced` and `rusty` are
    gone: they graded a person, and levelling language turns a neutral record
    into a curriculum that claims more than corroboration can support.

    There is no decay. A Technique that recurred did recur, and a month of
    rain does not make that untrue - so the record keeps saying so. Wanting a
    refresher is a *selection* concern and lives in the Scout's ranking, which
    reads ``last_observed``, rather than a state that quietly expires.
    """

    UNOBSERVED = "unobserved"
    #: The evidence has seen it at least once.
    OBSERVED = "observed"
    #: Corroborated three separate times: two lenses agreeing, each time.
    RECURRING = "recurring"


class TechniqueState(BaseModel):
    """What the Technique Map holds about one Technique for one photographer.

    ``corroborated`` is what moves the status, not ``best_score``. The score
    belongs to the whole frame: one photograph demonstrating six techniques
    hands the same number to all six, so promoting on it credits every
    technique in the frame for whatever the best one earned. Agreement and
    confidence are the only signals that are *about this technique*.
    """

    user_id: str
    technique_id: str
    status: TechniqueStatus = TechniqueStatus.UNOBSERVED
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
    last_observed: datetime | None = None
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


class TendencyGrade(BaseModel):
    """What the Scout's own advice was aimed at, and whether it landed.

    Decision 37: an agent that never checks its own recommendations is a
    critique queue, not a coach. The dimension this quest pushed against is
    frozen here at issue time, and when later shots arrive the counts are
    compared - arithmetic, no model adjudicating.

    What this deliberately does not claim: that moved counts mean better
    photographs. Behaviour change is the measurable thing. Quality stays the
    panel's opinion and is labelled as such wherever it appears.
    """

    #: The dimension id the challenge came from, or "dwell".
    source: str = ""
    #: The sentence the photographer was shown: "12 of 18 readable: centred".
    citation: str = ""
    #: Bucket -> count for that dimension, frozen when the quest was issued.
    at_issue: dict[str, int] = Field(default_factory=dict)
    #: Filled in when the grading runs. None until then.
    moved: bool | None = None
    #: What changed, in one plain sentence.
    outcome: str = ""
    graded_at: datetime | None = None


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
    #: The tendency this quest was aimed at, and whether the aim was any good.
    tendency: TendencyGrade | None = None
    status: QuestStatus = QuestStatus.OPEN
    verdicts: list[Verdict] = Field(default_factory=list)
    issued_at: datetime = Field(default_factory=now)
    due_at: datetime | None = None
    closed_at: datetime | None = None


# --- audit trail ----------------------------------------------------------


class JourneyUpdate(BaseModel):
    """The agent's current conclusion about the photographer (decision 39).

    The finished artifact of the whole product, and the thing the hobbyist
    actually wanted when they installed a photography app: not a quest ticket
    closed, an honest answer to *what kind of photographer am I becoming, and
    am I improving?* One paragraph, written when the Tendency Profile
    meaningfully moves rather than on a schedule.

    Every clause is anchored: ``evidence`` holds the counts and corroborations
    the writer was given, and the writer may not say anything it cannot point
    at. What it may never claim is that the photographs got *better* — that is
    the panel's opinion and is labelled as such. It claims that the
    photographer changed, which is arithmetic, and where Keepers exist that
    they are moving toward what they value, which is the photographer's own
    verdict rather than the model's.
    """

    id: str
    user_id: str
    #: The paragraph the photographer reads.
    body: str
    #: What it was written from: exploration per dimension, what widened, which
    #: techniques became repeatable, the dwell figure, the keeper lifts.
    evidence: list[str] = Field(default_factory=list)
    #: Dimension ids that widened since the last update, widest first.
    widened: list[str] = Field(default_factory=list)
    #: The profile as it stood when this was written: dimension id → bucket →
    #: count. Stored so the *next* update can diff against it exactly, rather
    #: than re-reporting the whole body of work as new every time.
    counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    #: Techniques that reached solid since the last update.
    became_solid: list[str] = Field(default_factory=list)
    #: How many shots the profile behind this one was built from.
    shots: int = 0
    #: True when the photographer had marked enough Keepers for the update to
    #: speak about taste rather than only about change.
    taste_is_known: bool = False
    created_at: datetime = Field(default_factory=now)


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
