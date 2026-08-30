"""The records Shoots keeps. Pydantic v2, stored as plain dicts in Firestore.

Vocabulary is docs/domain-model.md. A *Shot* is one photo or video file. The
*Analyst* turns a Shot into *Evidence* for Techniques. The *Technique Map* is
the per-user state of every Technique. An *Experiment* asks for one Technique
and says, in machine-checkable terms, what counts as done - and keeps the
record of how it went, which is the *Experiment Record*.
"""

import math
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


def now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _finite_coordinate(value: Any, maximum: float) -> float | None:
    """Reject malformed GPS at the record boundary instead of storing NaN."""
    if value is None:
        return None
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(coordinate) or not -maximum <= coordinate <= maximum:
        return None
    return coordinate


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


class SignalScope(StrEnum):
    PHOTOGRAPHER = "photographer"
    INSPIRATION = "inspiration"
    SHOOT = "shoot"
    SCENE = "scene"
    SHOT = "shot"
    EXPERIMENT = "experiment"


class PhotographerSignalKind(StrEnum):
    INTENT = "intent"
    CONSTRAINT = "constraint"
    PREFERENCE = "preference"
    SOURCE_ROLE = "source_role"


class SignalSource(StrEnum):
    DIRECT_STATEMENT = "direct_statement"
    CONFIRMED_SUGGESTION = "confirmed_suggestion"
    PHOTOGRAPHER_ACTION = "photographer_action"


class PhotographerSignal(BaseModel):
    """One attributable, correctable statement owned by the Photographer."""

    id: str
    user_id: str
    scope: SignalScope = SignalScope.PHOTOGRAPHER
    scope_id: str = ""
    kind: PhotographerSignalKind
    value: str
    source: SignalSource
    source_event_id: str = ""
    transcript_digest: str = ""
    created_at: datetime = Field(default_factory=now)
    confirmed_at: datetime | None = None
    supersedes_signal_id: str = ""
    superseded_at: datetime | None = None
    expires_at: datetime | None = None


class RecordMode(StrEnum):
    """Whether this account is a real Photographer record or a read-only fixture."""

    REAL = "real"
    SAMPLE = "sample"


class MemoryRecall(BaseModel):
    """Bounded Photographer memory assembled for one agent purpose."""

    role: str
    purpose: str
    scope: SignalScope = SignalScope.PHOTOGRAPHER
    scope_id: str = ""
    signals: list[PhotographerSignal] = Field(default_factory=list)
    input_signal_ids: list[str] = Field(default_factory=list)
    blind_spots: list[str] = Field(default_factory=list)
    memory_version: str = "photographer-memory-1"


class User(BaseModel):
    id: str
    email: str
    name: str = ""
    picture: str = ""
    record_mode: RecordMode = RecordMode.REAL
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

    @field_validator("last_latitude", mode="before")
    @classmethod
    def validate_last_latitude(cls, value: Any) -> float | None:
        return _finite_coordinate(value, 90)

    @field_validator("last_longitude", mode="before")
    @classmethod
    def validate_last_longitude(cls, value: Any) -> float | None:
        return _finite_coordinate(value, 180)


# --- shots ----------------------------------------------------------------


class ShotKind(StrEnum):
    PHOTO = "photo"
    VIDEO = "video"


class ShotSource(StrEnum):
    """Where the stable source reference and original bytes came from."""

    DRIVE = "drive"
    DRIVE_PICKER = "drive_picker"
    WEB_UPLOAD = "web_upload"
    ANDROID = "android"


class SourceRole(StrEnum):
    """Whether an ambiguous manual source depicts the Photographer's own work."""

    MINE = "mine"
    INSPIRATION = "inspiration"


class ShotStatus(StrEnum):
    NEW = "new"
    #: Ingest owns this Shot until ``ingesting_at`` expires. This prevents two
    #: at-least-once deliveries from measuring and writing the same file at once.
    INGESTING = "ingesting"
    INGESTED = "ingested"
    #: The panel is running right now. Written before the first model call so
    #: a redelivery mid-flight skips instead of re-paying for four to six of
    #: them; ``analysing_at`` dates the claim so a dead attempt cannot strand
    #: the shot here (see ``services/analyst.py``).
    ANALYSING = "analysing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class CaptureTimeAuthority(StrEnum):
    UNKNOWN = "unknown"
    EXIF_OFFSET = "exif_offset"
    ANDROID_SOURCE = "android_source"


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
    #: Civil offset recorded beside DateTimeOriginal. Absent means the wall
    #: clock must not support sunrise, sunset, or night claims.
    capture_utc_offset_minutes: int | None = Field(default=None, ge=-840, le=840)
    capture_time_authority: CaptureTimeAuthority = CaptureTimeAuthority.UNKNOWN
    #: From the GPS block when the camera wrote one. Feeds experiment timing.
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("latitude", mode="before")
    @classmethod
    def validate_latitude(cls, value: Any) -> float | None:
        return _finite_coordinate(value, 90)

    @field_validator("longitude", mode="before")
    @classmethod
    def validate_longitude(cls, value: Any) -> float | None:
        return _finite_coordinate(value, 180)


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
    #: The adapter that supplied this Shot. Existing stored records default to
    #: Drive so the source migration does not rewrite the archive.
    source: ShotSource = ShotSource.DRIVE
    #: Stable inside that adapter. Redelivery of the same reference is a no-op.
    source_id: str = ""
    #: Drive import compatibility and reviewed-output linkage. Empty for direct
    #: Android ingress.
    drive_file_id: str = ""
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
    #: Set when the user shot this for a specific experiment.
    experiment_id: str = ""
    #: Explicit Explore Variation frozen by the Capture Session. Empty for
    #: free Shots and Reproduce.
    variation_id: str = ""
    #: The explicit system-camera batch that froze this association. Empty for
    #: free Shots and legacy/manual Experiment submissions.
    capture_session_id: str = ""
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
    #: Legacy camera pitch, degrees from level: negative is aimed down,
    #: positive up. Phone Source cannot recover device attitude from gallery
    #: media, so new Android imports normally leave it empty.
    pitch_deg: float | None = None
    #: The reviewed copy the Scribe wrote back into the user's Drive.
    drive_review_id: str = ""
    drive_review_url: str = ""
    error: str = ""
    captured_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=now)
    #: When Ingest atomically claimed this Shot. A stale claim may be retried.
    ingesting_at: datetime | None = None
    #: When the panel claimed this shot. Read only while the status is
    #: ANALYSING, to tell an attempt in flight from one that died.
    analysing_at: datetime | None = None
    #: A manual source-role correction preserves this historical record while
    #: removing it from every current Photographer projection.
    superseded_at: datetime | None = None
    superseded_by_inspiration_id: str = ""
    analyzed_at: datetime | None = None


class Inspiration(BaseModel):
    """Reference material explicitly kept outside Photographer-derived memory."""

    id: str
    user_id: str
    source: ShotSource
    source_id: str
    filename: str
    mime_type: str
    blobs: dict[str, str] = Field(default_factory=dict)
    source_shot_id: str = ""
    created_at: datetime = Field(default_factory=now)
    superseded_at: datetime | None = None
    restored_shot_id: str = ""


# --- analysis -------------------------------------------------------------


class VisualPathRole(StrEnum):
    BOUNDARY = "boundary"
    EDGE = "edge"
    TRAIL = "trail"
    FLOW = "flow"
    AXIS = "axis"
    OTHER = "other"


class VisualPath(BaseModel):
    """One ordered, cell-addressed visible path and its optional target."""

    points: list[str] = Field(default_factory=list)
    leads_to: list[str] = Field(default_factory=list)
    role: VisualPathRole = VisualPathRole.OTHER


class VisualRegionRole(StrEnum):
    SUBJECT = "subject"
    TARGET = "target"
    FOREGROUND = "foreground"
    MIDGROUND = "midground"
    BACKGROUND = "background"
    FRAME = "frame"
    REFLECTION = "reflection"
    SOURCE = "source"
    REPEAT = "repeat"
    EXCEPTION = "exception"
    HIGHLIGHT = "highlight"
    LIGHT = "light"
    SHADOW = "shadow"
    WARM = "warm"
    COOL = "cool"
    SHARP = "sharp"
    BLURRED = "blurred"
    NEGATIVE_SPACE = "negative_space"
    OTHER = "other"


class VisualRegion(BaseModel):
    """One cell-bounded member of a pair, plane sequence, or instance set."""

    cells: list[str] = Field(default_factory=list)
    role: VisualRegionRole = VisualRegionRole.OTHER
    order: int = Field(default=0, ge=0, le=99)


class VisualArtifactAuthority(StrEnum):
    MEASURED = "measured"
    LOCATED_MODEL_READ = "located_model_read"
    RELATIONAL_MODEL_READ = "relational_model_read"
    MANUAL_FIXTURE = "manual_fixture"
    UNRESOLVED = "unresolved"


class VisualArtifactStatus(StrEnum):
    RENDERED = "rendered"
    FALLBACK = "fallback"
    UNRESOLVED = "unresolved"


class VisualArtifactVerification(StrEnum):
    NOT_RUN = "not_run"
    MEASURED = "measured"
    BOUNDED = "bounded"
    FALLBACK = "fallback"
    REJECTED = "rejected"


class VisualArtifactKind(StrEnum):
    HUE_MASK = "hue_mask"
    SATURATION_MAP = "saturation_map"
    LUMINANCE_MAP = "luminance_map"
    SHARPNESS_MAP = "sharpness_map"
    NOISE_MAP = "noise_map"
    EDGE_MAP = "edge_map"
    VERIFIED_PATHS = "verified_paths"
    BOKEH_INSTANCES = "bokeh_instances"
    BLUR_DIRECTION = "blur_direction"
    RADIAL_BLUR = "radial_blur"
    FACE_LANDMARKS = "face_landmarks"
    SUBJECT_CONTOUR = "subject_contour"
    EXIF_RECEIPT = "exif_receipt"
    GEOMETRY = "geometry"


class VisualEvidenceArtifact(BaseModel):
    """Code-rendered support for one Technique Evidence claim.

    A measured artifact states only the measurement it actually renders. The
    Technique interpretation remains the Analyst's model read unless hard
    Evidence separately settles it.
    """

    kind: VisualArtifactKind
    authority: VisualArtifactAuthority
    status: VisualArtifactStatus = VisualArtifactStatus.RENDERED
    verification: VisualArtifactVerification = VisualArtifactVerification.NOT_RUN
    refinement_count: int = Field(default=0, ge=0, le=1)
    blob_path: str = ""
    label: str = ""
    legend: str = ""
    metrics: dict[str, float | int | str] = Field(default_factory=dict)
    source_digest: str = ""
    renderer_version: str = ""
    fallback_reason: str = ""


class TechniqueEvidence(BaseModel):
    """One technique the Analyst believes this shot demonstrates."""

    technique_id: str
    confidence: float = Field(ge=0, le=1)
    #: Cells where the evidence is visible. Empty for global qualities.
    cells: list[str] = Field(default_factory=list)
    #: Separate ordered geometry for line-shaped Evidence. Never reconstructed from cells.
    paths: list[VisualPath] = Field(default_factory=list)
    #: Separate semantic members for pair, plane, enclosure, and instance Evidence.
    regions: list[VisualRegion] = Field(default_factory=list)
    #: Deterministic pixels or an explicit fallback created after the panel.
    visual_artifact: VisualEvidenceArtifact | None = None
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


class MoveWarrant(StrEnum):
    UNSPECIFIED = "unspecified"
    VISIBLE_CONFLICT = "visible_conflict"
    SUBJECT_SEPARATION = "subject_separation"
    FRAME_EDGE = "frame_edge"
    LIGHT = "light"
    GUIDE = "guide"
    VARIATION = "variation"


class Move(BaseModel):
    """One concrete change to the frame."""

    what: str
    kind: MoveKind = MoveKind.MOVE
    from_cells: list[str] = Field(default_factory=list)
    to_cells: list[str] = Field(default_factory=list)
    reason: str = ""
    warrant: MoveWarrant = MoveWarrant.UNSPECIFIED
    challenges_technique_ids: list[str] = Field(default_factory=list)


class Composition(BaseModel):
    subject_cells: list[str] = Field(default_factory=list)
    #: The subject's centre in frame units (0-1), when the Composer gave one
    #: that falls inside ``subject_cells``. Cells quantise to a seventh of the
    #: width; a guide that measures against a thirds line needs finer than that.
    subject_x: float | None = None
    subject_y: float | None = None
    #: Which compositional guide a human should see over this frame
    #: (``domain/guides.py``), chosen from the retained spatial Techniques.
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
    #: Digest of the complete Analyst prompt bundle used for this reading.
    prompt_version: str = ""
    techniques: list[TechniqueEvidence] = Field(default_factory=list)
    composition: Composition = Field(default_factory=Composition)
    #: Neutral, cell-referenced description (Feldman's first step), before judgement.
    observations: list[str] = Field(default_factory=list)
    #: What the arithmetic says is wrong with the frame (domain/findings.py).
    #: Computed after the vote, so a technique can excuse its own side effect.
    findings: list[Finding] = Field(default_factory=list)
    critique: str = ""
    #: Seconds each lens took; a lens missing here did not answer.
    panel: dict[str, float] = Field(default_factory=dict)
    #: Sightings that lost the vote: [{lens, technique_id, confidence}]. Shown, not counted.
    dissent: list[dict[str, Any]] = Field(default_factory=list)
    #: Set when the panel could not call this frame: every lens saw something
    #: and no two saw the same thing (decision 38). The findings still stand -
    #: they are arithmetic - but nothing here should be read as a verdict, and
    #: the review says so rather than averaging three opinions into one.
    abstained: str = ""
    created_at: datetime = Field(default_factory=now)


class TeachingAuthority(StrEnum):
    MEASURED = "measured"
    MODEL_READ = "model_read"


class VisualMarkKind(StrEnum):
    NONE = "none"
    REGION = "region"
    LINE = "line"
    FRAME = "frame"
    POINT = "point"
    WHOLE_FRAME = "whole_frame"
    FINDING = "finding"
    MOVE = "move"
    CROP = "crop"
    PAIR = "pair"
    INSTANCES = "instances"
    PLANES = "planes"


class VisualMark(BaseModel):
    """Drawable support for one visible Shot-story claim."""

    kind: VisualMarkKind = VisualMarkKind.NONE
    cells: list[str] = Field(default_factory=list)
    to_cells: list[str] = Field(default_factory=list)
    paths: list[VisualPath] = Field(default_factory=list)
    regions: list[VisualRegion] = Field(default_factory=list)
    visual_artifact: VisualEvidenceArtifact | None = None
    technique_id: str = ""
    finding_id: str = ""


class ShotTeachingReceipt(BaseModel):
    """One compact, evidence-labelled teaching action for a Shot read."""

    keep_title: str = ""
    keep_proof: str = ""
    keep_technique_id: str = ""
    keep_authority: TeachingAuthority | None = None
    keep_cells: list[str] = Field(default_factory=list)
    keep_mark: VisualMark = Field(default_factory=VisualMark)
    notice_title: str = ""
    notice_proof: str = ""
    notice_finding_id: str = ""
    notice_authority: TeachingAuthority | None = None
    notice_cells: list[str] = Field(default_factory=list)
    notice_mark: VisualMark = Field(default_factory=VisualMark)
    try_text: str = ""
    try_reason: str = ""
    try_kind: MoveKind | None = None
    try_from_cells: list[str] = Field(default_factory=list)
    try_to_cells: list[str] = Field(default_factory=list)
    try_mark: VisualMark = Field(default_factory=VisualMark)
    visible_check: str = ""
    check_mark: VisualMark = Field(default_factory=VisualMark)
    primary_layer: str = "clean"
    guide: str = ""


# --- technique map --------------------------------------------------------


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

    ``corroborated`` is what moves the status. Whole-Shot scores were removed:
    one number cannot measure every Technique visible inside the same Shot.
    Agreement and confidence are the signals that are about this Technique.

    Earlier records may contain score keys. Pydantic ignores those legacy
    extras; new Technique states never carry them (decision 61).
    """

    user_id: str
    technique_id: str
    status: TechniqueStatus = TechniqueStatus.UNOBSERVED
    attempts: int = 0
    #: Attempts where more than one lens saw it and both were sure.
    corroborated: int = 0
    #: Highest voted confidence this technique has ever reached.
    best_confidence: float = 0.0
    last_observed: datetime | None = None
    #: Shot ids, newest last, capped by the Cartographer.
    shot_ids: list[str] = Field(default_factory=list)
    #: Independent evidence axes. ``attempts`` and ``corroborated`` mirror the
    #: first two until their legacy names finish migrating.
    sightings: int = 0
    corroborated_shots: int = 0
    distinct_scenes: int = 0
    distinct_shoots: int = 0
    #: Explicit result-Shot attempts; session figures below prevent one burst from
    #: masquerading as repeated control.
    reproduce_attempts: int = 0
    criteria_met_results: int = 0
    #: Settled Capture Sessions keep natural recurrence separate from deliberate tests.
    reproduce_sessions: int = 0
    evaluable_reproduce_sessions: int = 0
    criteria_met_sessions: int = 0
    abstentions: int = 0
    positive_keeper_shots: int = 0
    supported_condition_coverage: dict[str, int] = Field(default_factory=dict)
    projection_version: str = ""
    input_digest: str = ""


# --- provenance -----------------------------------------------------------


class ModelProvenance(BaseModel):
    """One model-read input a longitudinal calculation depended on."""

    model: str
    prompt_version: str


class Provenance(BaseModel):
    """Where a longitudinal claim came from, so it can be checked or replayed.

    A claim about a body of work is not checkable the way a single Finding is:
    the reader cannot open one file and see the figure. What makes it honest
    instead is knowing exactly which Shots it was computed from, how many, by
    which version of the arithmetic, and - where a model wrote the words -
    under which model and which prompt.

    Re-running the same ``calc_version`` over the same ``shot_ids`` reproduces
    deterministic dimensions. Dimensions sourced from an Analysis are
    traceable through ``inputs`` but are not promised to regenerate identically.
    """

    #: Every Shot the claim was computed from, in the order they were read.
    shot_ids: list[str] = Field(default_factory=list)
    #: How many that is. Stored beside the ids so a reader sees the sample size
    #: without counting, and so a truncated id list still reports honestly.
    sample_size: int = 0
    #: The version of the pure arithmetic that produced the figures.
    calc_version: str = ""
    #: Set only where a model contributed language to the claim.
    model: str = ""
    prompt_version: str = ""
    #: Distinct Analyst versions behind model-read dimensions in this sample.
    inputs: list[ModelProvenance] = Field(default_factory=list)
    #: Shot id -> digest of the stored model-read fields used by the Profile.
    analysis_versions: dict[str, str] = Field(default_factory=dict)
    computed_at: datetime = Field(default_factory=now)


# --- experiments ---------------------------------------------------------------


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


class Variation(BaseModel):
    """One optional decision route inside an Explore or Compare."""

    id: str
    title: str
    instruction: str
    inversion: bool = False


class VariationObservation(BaseModel):
    """Structured Analyst Evidence observed for one explicit Explore result."""

    variation_id: str
    shot_id: str
    technique_ids: list[str] = Field(default_factory=list)
    corroborated_technique_ids: list[str] = Field(default_factory=list)
    guide: str = ""
    finding_ids: list[str] = Field(default_factory=list)
    abstained: str = ""
    model: str = ""
    prompt_version: str = ""
    observed_at: datetime = Field(default_factory=now)


class Reference(BaseModel):
    title: str
    url: str


class ExperimentType(StrEnum):
    """Which of the three questions this Experiment asks (decision 43).

    Scout issues ``REPRODUCE`` from corroborated Techniques in Photographer-marked
    Keepers and corrected ``EXPLORE`` from a supported Tendency Direction or an
    explicit supported Technique. ``COMPARE`` remains deliberately unissued until
    its paired Variation and Photographer-owned preference records exist.
    """

    #: Widen a dimension the archive barely uses.
    EXPLORE = "explore"
    #: Repeat a Keeper-associated pattern deliberately, to see whether it was
    #: luck or something the photographer can call on.
    REPRODUCE = "reproduce"
    #: Change one variable, keep both frames, and let the photographer say
    #: which result they value. The model does not pick the winner.
    COMPARE = "compare"


class ExperimentStatus(StrEnum):
    OPEN = "open"
    #: The Criteria were met. "Passed" graded the photographer; an Experiment
    #: is something they tried, and it either completed or it did not.
    COMPLETED = "completed"
    #: The photographer ended the offer without making a claim about the
    #: Technique or the result. ``SKIPPED`` remains readable for old records.
    LEFT = "left"
    SKIPPED = "skipped"  # the human gate: the photographer declined it
    EXPIRED = "expired"


class Verdict(BaseModel):
    """One submitted Shot measured against one Experiment's declared Criteria.

    It answers the Criteria and nothing else (decision 46). It is not a mark
    for the photograph and not a grade for the photographer, which is why the
    field is ``criteria_met`` rather than ``passed``: a person passes or fails,
    a declared check is met or is not.
    """

    shot_id: str
    criteria_met: bool
    exif_checks: dict[str, bool | None] = Field(default_factory=dict)
    vision_checks: dict[str, float] = Field(default_factory=dict)
    feedback: str
    #: An earlier Shot of the same Technique the feedback was written against.
    #: Chosen by Keeper first, then corroboration, then recency - never by a
    #: score, so it is "one of your earlier ones", not "your best".
    compared_with: str = ""
    judged_at: datetime = Field(default_factory=now)


class Baseline(BaseModel):
    """The measurement an Experiment was aimed at, frozen before any result.

    Frozen at issue time on purpose: a baseline computed afterwards is not a
    baseline, it is a story told backwards. Everything here is plain counts and
    the version of the arithmetic that produced them, so the comparison can be
    replayed from the store years later without a model, a photograph or a
    prompt.

    A Baseline exists only when the photographer's own tendency actually chose
    the Experiment. Advice that was picked for another reason is not graded
    against a tendency it was never aimed at (``services/scout.py``).
    """

    #: The dimension id the Experiment Direction came from, or "dwell".
    source: str = ""
    #: The sentence the photographer was shown: "12 of 18 readable: centred".
    #: Arithmetic, not prose - it is rendered verbatim rather than paraphrased.
    citation: str = ""
    #: Bucket -> count for that dimension, frozen when the Experiment was issued.
    at_issue: dict[str, int] = Field(default_factory=dict)
    #: The version of the arithmetic that froze ``at_issue``. A comparison is
    #: only meaningful against the calculation that produced its baseline, so a
    #: bump here makes the two sides incomparable rather than merely stale.
    calc_version: str = ""
    #: Which Shots the figures came from. No model wrote the citation - it is an
    #: f-string over counts - so no model or prompt is recorded here.
    provenance: Provenance = Field(default_factory=Provenance)
    frozen_at: datetime = Field(default_factory=now)


class ChangeState(StrEnum):
    """The three answers to "does comparable behaviour differ now?"

    The third is the one that makes the other two worth anything. Without it a
    photographer who simply did not go out reads as advice that failed, and
    good advice gets retired on no evidence at all.
    """

    CHANGED = "changed"
    UNCHANGED = "unchanged"
    #: Not a polite "no". The system declining to compare two samples that
    #: cannot be compared, and saying which of them was not enough.
    INSUFFICIENT = "insufficient evidence"


class Comparability(StrEnum):
    """Why two samples could, or could not, be set beside each other.

    Recorded separately from the answer because the reasons differ in kind:
    one of them can go away on its own, and the others never will.
    """

    COMPARABLE = "comparable"
    #: Not yet - the photographer has not shot enough since. Checked again.
    TOO_FEW_SHOTS = "too few shots"
    #: The baseline was frozen by a different ``CALC_VERSION``. Diffing across
    #: it would report a change the photographer never made. Never re-checked.
    DIFFERENT_ARITHMETIC = "different arithmetic"
    #: A model-read dimension changed Analyst model or prompt provenance.
    DIFFERENT_MODEL_READING = "different model reading"
    #: Nothing measures that dimension any more. Never re-checked.
    UNKNOWN_DIMENSION = "unknown dimension"
    #: The baseline predates the record of how many Shots it was taken over, so
    #: there is no honest way to say how much has been shot since. Only ever
    #: true of Experiments issued before ``Baseline.provenance`` existed.
    UNRECORDED_SAMPLE = "unrecorded sample"
    #: One or more exact Baseline Shots no longer exist in the archive.
    BASELINE_SHOTS_MISSING = "baseline shots missing"


class Change(BaseModel):
    """Whether comparable behaviour differs now from the frozen Baseline.

    The coach grading its own advice (decision 37): an agent that never checks
    its own recommendations is a critique queue. Both sides are plain counts,
    so no model adjudicates whether the advice landed.

    What a Change never claims, and what the wording is written to avoid: that
    the Experiment *caused* the difference, or that the photographs got better.
    Behaviour is measurable. Causation is not available from two frozen counts,
    and quality stays the panel's opinion and is labelled as one.
    """

    state: ChangeState
    comparability: Comparability = Comparability.COMPARABLE
    #: What the counts say, in one plain sentence. Never a causal one.
    outcome: str = ""
    #: Buckets that were empty at issue and have something in them now.
    new_buckets: list[str] = Field(default_factory=list)
    #: Shots taken since the Baseline was frozen.
    added: int = 0
    #: Stamped by the service that recorded it. The pure arithmetic leaves it
    #: unset, so a Change stays reproducible from the counts alone.
    checked_at: datetime | None = None

    @property
    def settled(self) -> bool:
        """Whether a later check could still reach a different answer.

        Only a sample that is merely too small can grow into one. A baseline
        frozen under other arithmetic never becomes comparable, so re-checking
        it forever would be noise.
        """
        return self.comparability is not Comparability.TOO_FEW_SHOTS


class ExperimentTiming(BaseModel):
    """Why the experiment lands when it does (domain/timing.py)."""

    light: str
    reason: str
    anchor: str = ""  # sunrise | sunset | dusk
    anchor_at: datetime | None = None


class ExperimentDirectionState(StrEnum):
    """What the Photographer chose before any Experiment exists."""

    SAVED = "saved"
    LEFT = "left"
    STARTED = "started"


class ExperimentDirection(BaseModel):
    """One optional later question grounded in existing Photographer Evidence.

    A Direction deliberately stops short of an Experiment. It carries no
    Criteria, deadline, Capture Session, Verdict, or inferred Intent.
    """

    id: str
    user_id: str
    source_shot_id: str
    technique_id: str
    technique_name: str
    question: str
    warrant_shot_ids: list[str] = Field(default_factory=list)
    reference_shot_id: str = ""
    corroborated_shots: int = 0
    distinct_shoots: int = 0
    state: ExperimentDirectionState = ExperimentDirectionState.SAVED
    started_experiment_id: str = ""
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class Experiment(BaseModel):
    """One bounded thing to try, and the durable record of how it went.

    This *is* the Experiment Record (decision 44): the reason it was set, its
    type, the frozen Baseline, the declared Criteria, the Verdicts that came
    back, and the Change afterwards - all on one row, all readable later. That
    is the point of it. Advice text alone leaves nothing behind to check, and a
    coach whose recommendations cannot be audited is just a critique queue with
    a friendlier tone.
    """

    id: str
    user_id: str
    technique_id: str
    type: ExperimentType = ExperimentType.EXPLORE
    title: str
    brief: str
    why_now: str  # the Scout's gap reasoning, shown to the user
    criteria: Criteria = Field(default_factory=Criteria)
    variations: list[Variation] = Field(default_factory=list)
    variation_observations: list[VariationObservation] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    reference_clip: str = ""  # blob path of the Veo clip
    #: When the push lands. The experiment exists before that; the phone waits.
    deliver_at: datetime | None = None
    delivered_at: datetime | None = None
    timing: ExperimentTiming | None = None
    #: The tendency this Experiment was aimed at, frozen before any result.
    #: None when the photographer's own work did not choose it.
    baseline: Baseline | None = None
    #: Reproduce freezes one exact marked Keeper before any result arrives.
    #: Empty for Explore, Compare, and legacy records.
    reference_shot_id: str = ""
    #: Exact Keeper or Tendency Evidence references that permitted Scout to
    #: offer this Experiment. Empty on legacy and explicitly requested records.
    warrant_shot_ids: list[str] = Field(default_factory=list)
    #: Every Shot explicitly submitted while this Experiment owned it. This
    #: includes an abstention, which creates no Verdict but remains a result.
    result_shot_ids: list[str] = Field(default_factory=list)
    #: Whether comparable behaviour differs now. None until it has been checked,
    #: and re-checked while the sample is only too small (``Change.settled``).
    change: Change | None = None
    status: ExperimentStatus = ExperimentStatus.OPEN
    verdicts: list[Verdict] = Field(default_factory=list)
    issued_at: datetime = Field(default_factory=now)
    due_at: datetime | None = None
    closed_at: datetime | None = None


# --- deconstructions ------------------------------------------------------


class DeconstructionSourceType(StrEnum):
    SHOOT = "shoot"
    EXPERIMENT = "experiment"


class DeconstructionStatus(StrEnum):
    NEEDS_COVER = "needs_cover"
    DRAFTED = "drafted"
    FAILED = "failed"


class DeconstructionPageKind(StrEnum):
    COVER = "cover"
    SHOOT_WORK = "shoot_work"
    COMPOSITION = "composition"
    LIGHT_COLOUR = "light_colour"
    TECHNIQUE = "technique"
    EXPLORE = "explore"
    REPRODUCE = "reproduce"
    CHANGE = "change"
    RECORD = "record"


class DeconstructionPage(BaseModel):
    """One claim and its exact visual and Evidence inputs."""

    kind: DeconstructionPageKind
    title: str
    claim: str
    shot_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    visual_layer: str = "original"
    blob_path: str = ""


class Deconstruction(BaseModel):
    """A photographer-controlled, shareable draft from stored Evidence."""

    id: str
    user_id: str
    source_type: DeconstructionSourceType
    source_id: str
    source_revision: int = 0
    status: DeconstructionStatus = DeconstructionStatus.NEEDS_COVER
    candidate_cover_shot_ids: list[str] = Field(default_factory=list)
    cover_shot_id: str = ""
    pages: list[DeconstructionPage] = Field(default_factory=list)
    suggested_caption: str = ""
    input_digest: str = ""
    rendering_version: str = "deconstruction-render-1"
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


# --- scenes and shoots ----------------------------------------------------


class ShootStatus(StrEnum):
    OPEN = "open"
    CLOSING = "closing"
    SETTLED = "settled"


class Scene(BaseModel):
    """One capture-continuous photographic situation inside a Shoot."""

    id: str
    user_id: str
    shoot_id: str
    grouping_revision: int = 1
    ordered_shot_ids: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    grouping_source: str = "capture_continuity"
    grouping_version: str = "scene-gap-1"


class Shoot(BaseModel):
    """One natural period of Camera activity containing one or more Scenes."""

    id: str
    user_id: str
    device_id: str = ""
    status: ShootStatus = ShootStatus.OPEN
    revision: int = 1
    current_record_revision: int = 0
    ordered_scene_ids: list[str] = Field(default_factory=list)
    ordered_shot_ids: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    last_capture_at: datetime | None = None
    closed_at: datetime | None = None
    grouping_version: str = "shoot-gap-1"


class EvidenceAuthority(StrEnum):
    """Whose evidence a Shoot receipt is allowed to present as fact."""

    MEASURED = "measured"
    MODEL_READ = "model_read"
    PHOTOGRAPHER_OWNED = "photographer_owned"


class ShootDimensionFigure(BaseModel):
    """One replayable distribution over a settled Shoot's exact members."""

    dimension_id: str
    label: str
    authority: EvidenceAuthority
    counts: dict[str, int] = Field(default_factory=dict)
    readable_shots: int = 0
    unreadable_shots: int = 0
    dominant: str = ""
    dominant_count: int = 0
    exploration: float = 0.0
    blind_spot: str = ""


class ShootTechniqueFigure(BaseModel):
    """Shot-level model Evidence without promotion to measured truth."""

    technique_id: str
    name: str
    authority: EvidenceAuthority = EvidenceAuthority.MODEL_READ
    observed_shot_ids: list[str] = Field(default_factory=list)
    corroborated_shot_ids: list[str] = Field(default_factory=list)


class ShootReceipt(BaseModel):
    """Short, deterministic account of how one Shoot was worked."""

    calc_version: str = ""
    summary: str = ""
    shot_count: int = 0
    scene_count: int = 0
    shots_per_scene: list[int] = Field(default_factory=list)
    readable_shot_count: int = 0
    unreadable_shot_ids: list[str] = Field(default_factory=list)
    keeper_shot_ids: list[str] = Field(default_factory=list)
    repeated: list[str] = Field(default_factory=list)
    varied: list[str] = Field(default_factory=list)
    blind_spots: list[str] = Field(default_factory=list)
    dimensions: list[ShootDimensionFigure] = Field(default_factory=list)
    techniques: list[ShootTechniqueFigure] = Field(default_factory=list)


class ScoutRoute(StrEnum):
    EXPLAIN = "explain"
    ASK = "ask"
    RECOMMEND = "recommend"
    EXPLORE = "explore"
    REPRODUCE = "reproduce"
    SILENCE = "silence"


class ScoutExecutionState(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class InterventionAttemptState(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    ENTERED = "entered"
    LEFT = "left"
    COMPLETED = "completed"


class InterventionOutcome(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    UNCHANGED = "unchanged"
    CHANGED = "changed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class InterventionRecord(BaseModel):
    """Replayable current projection of one immutable Scout decision's outcome."""

    id: str
    user_id: str
    shoot_id: str
    shoot_revision: int
    route: ScoutRoute
    technique_id: str = ""
    question_id: str = ""
    recommendation_id: str = ""
    recommendation_option_id: str = ""
    experiment_id: str = ""
    warrant_shot_ids: list[str] = Field(default_factory=list)
    attempt_state: InterventionAttemptState = InterventionAttemptState.NOT_APPLICABLE
    observable_outcome: InterventionOutcome = InterventionOutcome.NOT_APPLICABLE
    result_shot_ids: list[str] = Field(default_factory=list)
    criteria_met_results: int = 0
    abstentions: int = 0
    variation_ids: list[str] = Field(default_factory=list)
    change_state: str = ""
    comparability: str = ""
    outcome_reason: str = ""
    delivered_at: datetime | None = None
    updated_at: datetime = Field(default_factory=now)


class ScoutWarrant(BaseModel):
    """Exact Evidence permitting one Scout route."""

    kind: str
    shoot_id: str
    shoot_revision: int
    shot_ids: list[str] = Field(default_factory=list)
    technique_id: str = ""
    reference_shot_id: str = ""
    detail: str = ""


class ScoutRejectedRoute(BaseModel):
    route: ScoutRoute
    reason: str


class ScoutQuestionOption(BaseModel):
    id: str
    label: str
    technique_id: str = ""


class ScoutQuestion(BaseModel):
    id: str = ""
    prompt: str = ""
    options: list[ScoutQuestionOption] = Field(default_factory=list)


class ScoutRecommendationOption(BaseModel):
    """One supported Experiment Direction Scout may recommend."""

    id: str
    technique_id: str
    technique_name: str
    experiment_type: ExperimentType
    title: str
    why_now: str
    warrant_shot_ids: list[str] = Field(default_factory=list)
    reference_shot_id: str = ""


class ScoutRecommendation(BaseModel):
    """One ranked suggestion that stops before an Experiment exists."""

    id: str = ""
    primary_option_id: str = ""
    options: list[ScoutRecommendationOption] = Field(default_factory=list)


class ScoutRecommendationAction(StrEnum):
    ACCEPT = "accept"
    NOT_TODAY = "not_today"
    JUST_SHOOTING = "just_shooting"


class ScoutDecision(BaseModel):
    """Code-gated intervention choice stored with one Shoot Record."""

    route: ScoutRoute = ScoutRoute.SILENCE
    reason: str = "No Shoot-level decision was recorded."
    warrant: list[ScoutWarrant] = Field(default_factory=list)
    rejected_routes: list[ScoutRejectedRoute] = Field(default_factory=list)
    input_shot_ids: list[str] = Field(default_factory=list)
    projection_versions: dict[str, str] = Field(default_factory=dict)
    policy_version: str = ""
    experiment_id: str = ""
    model: str = ""
    prompt_version: str = ""
    execution_state: ScoutExecutionState = ScoutExecutionState.COMPLETED
    execution_detail: str = ""
    attempt_state: InterventionAttemptState = InterventionAttemptState.NOT_APPLICABLE
    observable_outcome: InterventionOutcome = InterventionOutcome.NOT_APPLICABLE
    question: ScoutQuestion = Field(default_factory=ScoutQuestion)
    recommendation: ScoutRecommendation = Field(default_factory=ScoutRecommendation)
    decided_at: datetime = Field(default_factory=now)
    executed_at: datetime | None = None


class ScoutAnswerState(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


class ScoutAnswer(BaseModel):
    """One immutable Photographer answer to a stored Scout Question."""

    id: str
    user_id: str
    question_id: str
    shoot_id: str
    shoot_revision: int
    option_id: str
    technique_id: str = ""
    intent_signal_id: str = ""
    experiment_id: str = ""
    state: ScoutAnswerState = ScoutAnswerState.PENDING
    detail: str = ""
    answered_at: datetime = Field(default_factory=now)


class DeconstructionAttempt(BaseModel):
    """What Scribe could prepare while this Shoot revision settled."""

    deconstruction_id: str = ""
    status: DeconstructionStatus | None = None
    detail: str = ""


class ShootRecord(BaseModel):
    """The terminal account for one immutable Shoot revision."""

    shoot_id: str
    user_id: str
    revision: int = 1
    scene_ids: list[str] = Field(default_factory=list)
    shot_ids: list[str] = Field(default_factory=list)
    run_outcomes: dict[str, str] = Field(default_factory=dict)
    unreadable_shot_ids: list[str] = Field(default_factory=list)
    receipt: ShootReceipt = Field(default_factory=ShootReceipt)
    scout: ScoutDecision = Field(default_factory=ScoutDecision)
    deconstruction: DeconstructionAttempt = Field(default_factory=DeconstructionAttempt)
    provenance: Provenance = Field(default_factory=Provenance)
    settled_at: datetime = Field(default_factory=now)


# --- audit trail ----------------------------------------------------------


class RunStage(StrEnum):
    INGEST = "ingest"
    ANALYST = "analyst"
    CARTOGRAPHER = "cartographer"
    SCOUT = "scout"
    JUDGE = "judge"
    SCRIBE = "scribe"


class RunStepState(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    RETRYING = "retrying"
    TERMINAL = "terminal"


class RunStatus(StrEnum):
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    TERMINAL = "terminal"


class CaptureSessionStatus(StrEnum):
    RESERVED = "reserved"
    COMMITTED = "committed"
    PROCESSING = "processing"
    SETTLED = "settled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CaptureMemberOutcome(StrEnum):
    PENDING = "pending"
    CRITERIA_MET = "criteria_met"
    CRITERIA_NOT_MET = "criteria_not_met"
    ABSTAINED = "abstained"
    TERMINAL = "terminal"
    OBSERVED = "observed"


class CaptureSessionMember(BaseModel):
    """One Camera source reference explicitly frozen into a Capture Session."""

    source_id: str
    order: int = Field(ge=0)
    shot_id: str = ""
    outcome: CaptureMemberOutcome = CaptureMemberOutcome.PENDING


class CaptureSession(BaseModel):
    """Explicit participation around one handoff to Android's system camera."""

    id: str
    user_id: str
    experiment_id: str
    variation_id: str = ""
    device_id: str
    device_label: str = "Android"
    status: CaptureSessionStatus = CaptureSessionStatus.RESERVED
    members: list[CaptureSessionMember] = Field(default_factory=list)
    representative_result_shot_id: str = ""
    summary: dict[str, int] = Field(default_factory=dict)
    reserved_at: datetime = Field(default_factory=now)
    expires_at: datetime
    committed_at: datetime | None = None
    evaluated_at: datetime | None = None
    settled_at: datetime | None = None
    notification_sent_at: datetime | None = None


class RunStep(BaseModel):
    state: RunStepState = RunStepState.PENDING
    outcome: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)
    settled_at: datetime | None = None


class Run(BaseModel):
    """The durable terminal account for one accepted Shot."""

    id: str
    user_id: str
    shot_id: str
    source: ShotSource
    experiment_id: str = ""
    capture_session_id: str = ""
    status: RunStatus = RunStatus.RUNNING
    steps: dict[str, RunStep] = Field(
        default_factory=lambda: {stage.value: RunStep() for stage in RunStage}
    )
    started_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
    completed_at: datetime | None = None


class JourneyUpdate(BaseModel):
    """The agent's current conclusion about the photographer (decision 39).

    The finished artifact of the whole product, and the thing the hobbyist
    actually wanted when they installed a photography app: not an experiment ticket
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
    #: Techniques became recurring, the dwell figure, and marked-Keeper counts.
    evidence: list[str] = Field(default_factory=list)
    #: Dimension ids that widened since the last update, widest first.
    widened: list[str] = Field(default_factory=list)
    #: The profile as it stood when this was written: dimension id → bucket →
    #: count. Stored so the *next* update can diff against it exactly, rather
    #: than re-reporting the whole body of work as new every time.
    counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    #: Every Technique that had reached `recurring` when this was written. Kept
    #: whole rather than as a delta so the next update can tell what is new by
    #: subtraction, the same way ``counts`` lets it diff the profile exactly.
    became_recurring: list[str] = Field(default_factory=list)
    #: How many shots the profile behind this one was built from.
    shots: int = 0
    #: True when the photographer had marked enough Keepers for the update to
    #: speak about taste rather than only about change.
    taste_is_known: bool = False
    #: Keeper state at the time of this update. Stored separately from the
    #: Shot distribution because an unmarked Shot is unknown, not disliked.
    keepers: int = 0
    keeper_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    #: Which Shots, how many, which arithmetic, which model and prompt.
    provenance: Provenance = Field(default_factory=Provenance)
    created_at: datetime = Field(default_factory=now)
    superseded_at: datetime | None = None
    superseded_reason: str = ""


class ActivityEvent(BaseModel):
    """Every agent step, durable. The live feed is a view of this."""

    id: str
    user_id: str
    agent: str  # ingest | analyst | cartographer | scout | judge | scheduler
    stage: str
    detail: dict[str, Any] = Field(default_factory=dict)
    shot_id: str = ""
    experiment_id: str = ""
    at: datetime = Field(default_factory=now)
