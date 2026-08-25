"""The Tendency Profile: the photographer is a distribution.

A single shot has no tendency. Twenty do: the same height, the same distance,
the same hour, the subject in the middle again. A **tendency** is a dimension
of the decision space whose values barely vary, and the word is chosen over
"habit" on purpose (decision 39) — a repeated centred composition might be
laziness or the beginning of a personal style, and nothing here can tell those
apart. This module describes; it never corrects.

What it may claim, in order of how hard the claim is:

* **counts** — how many shots landed in each bucket. Always safe, always shown
  first, always re-derivable from the file each one came from.
* **exploration** — normalised entropy over a dimension's buckets: 0 when every
  shot landed in one, 1 when they are spread evenly. A number about the spread
  of a distribution, not about anybody's talent.
* **keeper lift** — how much likelier a photographer is to keep a shot from one
  bucket than from their work as a whole. This is the only place taste enters
  the system (decision 40), it comes from the photographer's own marks and
  never from the panel's score, and it stays silent until there are enough of
  them to mean anything.

Pure. No I/O, no model call, and every function here can be replayed over the
stored corpus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from math import log, sqrt

from app.domain import sun
from app.domain import tone as tone_rules
from app.domain.entities import Analysis, Shot

# --- how sure we have to be before we say anything ------------------------------

#: Below this many readable shots a dimension shows its counts and claims
#: nothing: with five frames, "you always centre the subject" is a sentence
#: about five frames.
MIN_SHOTS_FOR_TENDENCY = 8

#: A dimension is narrow enough to be worth a challenge below this exploration.
NARROW_BELOW = 0.55

#: Keeper lift needs both a habit of marking and a bucket with something in it.
MIN_KEEPERS_FOR_LIFT = 5
MIN_BUCKET_FOR_LIFT = 3

#: Two shots inside this gap belong to the same scene. Working a scene means
#: staying; walking on and shooting something else is a new one.
SCENE_GAP = timedelta(minutes=4)


# --- the decision space ---------------------------------------------------------


@dataclass(frozen=True)
class Dimension:
    """One axis of a photographic decision, and the buckets it falls into."""

    id: str
    #: What the photographer reads, as a noun phrase: "where you put the subject".
    label: str
    buckets: tuple[str, ...]
    #: Set when the measurement is not available from every source, so the
    #: profile can name its own blind spots instead of implying completeness.
    blind: str = ""


PLACEMENT = Dimension(
    id="placement",
    label="where you put the subject",
    buckets=("centred", "off centre", "near the edge"),
)
FRAMING = Dimension(
    id="framing",
    label="how close you get",
    buckets=("wide", "medium", "close"),
)
LIGHT = Dimension(
    id="light",
    label="the light you shoot in",
    buckets=("golden hour", "blue hour", "night", "open day"),
    blind="needs the time and place the camera recorded",
)
KEY = Dimension(
    id="key",
    label="how bright you keep the frame",
    buckets=("low key", "mid key", "high key"),
)
PALETTE = Dimension(
    id="palette",
    label="the colour you work in",
    buckets=("warm", "neutral", "cool"),
)
ORIENTATION = Dimension(
    id="orientation",
    label="how you hold the camera",
    buckets=("landscape", "portrait", "square"),
)
HEIGHT = Dimension(
    id="height",
    label="the height you shoot from",
    buckets=("low", "eye level", "high"),
    blind="only measured for shots taken through the Shoots camera",
)

DIMENSIONS: tuple[Dimension, ...] = (
    PLACEMENT,
    FRAMING,
    LIGHT,
    KEY,
    PALETTE,
    ORIENTATION,
    HEIGHT,
)
BY_ID = {d.id: d for d in DIMENSIONS}


# --- reading one shot -----------------------------------------------------------

#: Radial distance from the frame's centre, in frame units. A thirds
#: intersection sits at 0.236, so "centred" has to stop well before it.
CENTRED_WITHIN = 0.10
EDGE_BEYOND = 0.28

#: Share of the frame's cells the subject covers.
WIDE_BELOW = 0.08
CLOSE_ABOVE = 0.25

#: Hue shares, as a percentage of the frame, before a palette leans.
LEANS_BY = 8.0


def _placement(shot: Shot, analysis: Analysis | None) -> str | None:
    if analysis is None:
        return None
    x, y = analysis.composition.subject_x, analysis.composition.subject_y
    if x is None or y is None:
        return None
    offset = sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2)
    if offset < CENTRED_WITHIN:
        return "centred"
    return "near the edge" if offset >= EDGE_BEYOND else "off centre"


def _framing(shot: Shot, analysis: Analysis | None) -> str | None:
    if analysis is None or not shot.grid:
        return None
    cells = len(analysis.composition.subject_cells)
    total = shot.grid.cols * shot.grid.rows
    if not cells or not total:
        return None
    share = cells / total
    if share < WIDE_BELOW:
        return "wide"
    return "close" if share > CLOSE_ABOVE else "medium"


def _light(shot: Shot, analysis: Analysis | None) -> str | None:
    """Where the sun was, by the same NOAA equations the Scout times quests
    with. Golden and blue hour are claims about the sun's position, which is
    why they can be bucketed at all."""
    exif = shot.exif
    when = exif.captured_at or shot.captured_at
    if when is None or exif.latitude is None or exif.longitude is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    times = sun.sun_times(when.date(), exif.latitude, exif.longitude)
    if times.polar:
        return None
    for at in (times.sunrise, times.sunset):
        if abs(when - at) <= tone_rules.GOLDEN_WINDOW:
            return "golden hour"
    if when < times.dawn or when > times.dusk:
        return "night"
    if when < times.sunrise or when > times.sunset:
        return "blue hour"
    return "open day"


def _key(shot: Shot, analysis: Analysis | None) -> str | None:
    if shot.tone.luma_mean <= 0:
        return None
    return tone_rules.band(shot.tone.luma_mean, tone_rules.KEY_BANDS)


def _palette(shot: Shot, analysis: Analysis | None) -> str | None:
    warm, cool = shot.tone.warm_share, shot.tone.cool_share
    if warm <= 0 and cool <= 0:
        return None
    if warm - cool >= LEANS_BY:
        return "warm"
    return "cool" if cool - warm >= LEANS_BY else "neutral"


def _orientation(shot: Shot, analysis: Analysis | None) -> str | None:
    if not shot.grid or not shot.grid.width or not shot.grid.height:
        return None
    ratio = shot.grid.width / shot.grid.height
    if ratio > 1.05:
        return "landscape"
    return "portrait" if ratio < 0.95 else "square"


def _height(shot: Shot, analysis: Analysis | None) -> str | None:
    """The camera's pitch when the shutter fired, which only the Shoots camera
    records. Every shot that arrived through Drive is silent here, and the
    profile says so rather than implying the dimension was explored."""
    pitch = getattr(shot, "pitch_deg", None)
    if pitch is None:
        return None
    if pitch <= -20:
        return "high"
    return "low" if pitch >= 20 else "eye level"


READERS = {
    PLACEMENT.id: _placement,
    FRAMING.id: _framing,
    LIGHT.id: _light,
    KEY.id: _key,
    PALETTE.id: _palette,
    ORIENTATION.id: _orientation,
    HEIGHT.id: _height,
}


def read_shot(shot: Shot, analysis: Analysis | None = None) -> dict[str, str]:
    """Where this one shot sits in the decision space. Dimensions that could
    not be read are absent rather than guessed."""
    point = {}
    for dim_id, reader in READERS.items():
        value = reader(shot, analysis)
        if value is not None:
            point[dim_id] = value
    return point


# --- the profile ----------------------------------------------------------------


@dataclass
class DimensionProfile:
    dimension: Dimension
    #: Bucket → how many shots landed there. Buckets with none are absent.
    counts: dict[str, int] = field(default_factory=dict)
    #: Bucket → how many of those the photographer marked a Keeper.
    keepers: dict[str, int] = field(default_factory=dict)
    #: Shots that could not be read on this dimension at all.
    unreadable: int = 0

    @property
    def n(self) -> int:
        return sum(self.counts.values())

    @property
    def readable(self) -> bool:
        """Enough shots to say anything beyond the counts themselves."""
        return self.n >= MIN_SHOTS_FOR_TENDENCY

    @property
    def dominant(self) -> str:
        """The bucket most of the work sits in. Ties break on bucket order, so
        the answer does not move between runs."""
        if not self.counts:
            return ""
        order = {b: i for i, b in enumerate(self.dimension.buckets)}
        return max(self.counts, key=lambda b: (self.counts[b], -order.get(b, 99)))

    @property
    def dominant_share(self) -> float:
        return self.counts.get(self.dominant, 0) / self.n if self.n else 0.0

    @property
    def unexplored(self) -> tuple[str, ...]:
        """Buckets of this dimension the photographer has never used."""
        return tuple(b for b in self.dimension.buckets if not self.counts.get(b))

    @property
    def exploration(self) -> float:
        """Normalised Shannon entropy: 0 when every shot landed in one bucket,
        1 when they are spread evenly across all of them."""
        n = self.n
        buckets = len(self.dimension.buckets)
        if n == 0 or buckets < 2:
            return 0.0
        entropy = -sum((c / n) * log(c / n) for c in self.counts.values() if c)
        return abs(entropy / log(buckets))  # abs so one full bucket reads 0.0, not -0.0

    @property
    def narrow(self) -> bool:
        return self.readable and self.exploration < NARROW_BELOW

    def keeper_lift(self, bucket: str, overall_rate: float) -> float | None:
        """How much likelier a shot from this bucket is to be kept than one from
        the photographer's work as a whole. ``None`` when there is not enough
        marking behind it to be worth a sentence."""
        shots = self.counts.get(bucket, 0)
        if shots < MIN_BUCKET_FOR_LIFT or overall_rate <= 0:
            return None
        return (self.keepers.get(bucket, 0) / shots) / overall_rate


#: Below this many frames a scene, the photographer takes one picture and walks
#: on. Working the scene — moving closer, lower, round the side, and comparing
#: real alternatives — is the second most common thing professionals say to do
#: (6 of 12 sources, ``docs/boring-shots-advice-research.md``) and the one that
#: shows up in timestamps alone, with no pixels involved.
WORKS_THE_SCENE = 2.5


@dataclass
class Dwell:
    """How long the photographer stays with one scene, clustered on the gap
    between captures.

    This is a tendency like the others, but it earns its own type because it is
    measured across shots rather than inside one: no frame can tell you whether
    its photographer stayed.
    """

    scenes: int = 0
    shots: int = 0
    #: The largest number of frames given to any one scene.
    longest: int = 0

    @property
    def per_scene(self) -> float:
        return self.shots / self.scenes if self.scenes else 0.0

    @property
    def readable(self) -> bool:
        return self.scenes >= MIN_SHOTS_FOR_TENDENCY // 2

    @property
    def walks_on(self) -> bool:
        """One frame and away. The tendency with the most professional advice
        behind it, and the cheapest to change."""
        return self.readable and self.per_scene < WORKS_THE_SCENE


@dataclass
class Profile:
    dimensions: dict[str, DimensionProfile] = field(default_factory=dict)
    shots: int = 0
    keepers: int = 0
    dwell: Dwell = field(default_factory=Dwell)

    @property
    def keeper_rate(self) -> float:
        return self.keepers / self.shots if self.shots else 0.0

    @property
    def taste_is_known(self) -> bool:
        """Whether the photographer has marked enough Keepers for lift to mean
        anything. Without this the profile can say "you changed" and must not
        say "you are moving toward what you value" (decision 39)."""
        return self.keepers >= MIN_KEEPERS_FOR_LIFT

    @property
    def blind_spots(self) -> tuple[str, ...]:
        """Dimensions that could not be read for most of the corpus, with the
        reason. Named rather than quietly dropped."""
        out = []
        for dim in DIMENSIONS:
            profile = self.dimensions.get(dim.id)
            if profile and profile.n >= MIN_SHOTS_FOR_TENDENCY:
                continue
            reason = dim.blind or "not measured on enough shots yet"
            out.append(f"{dim.label}: {reason}")
        return tuple(out)

    def narrowest(self) -> DimensionProfile | None:
        """The dimension with the least variation, among those with enough
        shots behind them to say so. What a challenge should push against.

        Ties are common and they matter: a corpus shot entirely in landscape
        puts orientation at zero exploration on day one, and left to sort
        alphabetically every photographer would be told to turn the phone
        sideways forever. So a tie goes first to the dimension with more shots
        behind it, then to ``DIMENSIONS`` order, which runs from the choices
        that change a photograph most to the ones that change it least.
        """
        candidates = [p for p in self.dimensions.values() if p.narrow]
        if not candidates:
            return None
        order = {d.id: i for i, d in enumerate(DIMENSIONS)}
        return min(candidates, key=lambda p: (p.exploration, -p.n, order[p.dimension.id]))


def build(
    rows: list[tuple[Shot, Analysis | None]],
    keeper_ids: set[str] | frozenset[str] = frozenset(),
) -> Profile:
    """The profile over a photographer's whole corpus. ``rows`` is every shot
    with its analysis where one exists; ``keeper_ids`` is what they marked."""
    profile = Profile(
        dimensions={d.id: DimensionProfile(dimension=d) for d in DIMENSIONS},
        shots=len(rows),
        keepers=sum(1 for shot, _ in rows if shot.id in keeper_ids),
        dwell=dwell(rows),
    )
    for shot, analysis in rows:
        point = read_shot(shot, analysis)
        kept = shot.id in keeper_ids
        for dim_id, dim_profile in profile.dimensions.items():
            bucket = point.get(dim_id)
            if bucket is None:
                dim_profile.unreadable += 1
                continue
            dim_profile.counts[bucket] = dim_profile.counts.get(bucket, 0) + 1
            if kept:
                dim_profile.keepers[bucket] = dim_profile.keepers.get(bucket, 0) + 1
    return profile


def dwell(rows: list[tuple[Shot, Analysis | None]]) -> Dwell:
    """Cluster the corpus into scenes on the gap between captures. A shot with
    no capture time is its own scene rather than being folded into a neighbour
    it may have nothing to do with."""
    times: list[datetime | None] = []
    for shot, _ in rows:
        when = shot.exif.captured_at or shot.captured_at
        if when is not None and when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        times.append(when)
    dated = sorted(t for t in times if t is not None)
    undated = len(times) - len(dated)

    sizes: list[int] = []
    previous: datetime | None = None
    for when in dated:
        if previous is not None and (when - previous) <= SCENE_GAP:
            sizes[-1] += 1
        else:
            sizes.append(1)
        previous = when
    sizes += [1] * undated
    return Dwell(scenes=len(sizes), shots=len(times), longest=max(sizes, default=0))


# --- did anything move? ---------------------------------------------------------


@dataclass
class Movement:
    """One dimension's change between two profiles. The arithmetic behind both
    the Journey Update and the coach grading its own advice (decision 37):
    behaviour moved or it did not, and no model adjudicates that."""

    dimension: Dimension
    was: float
    now: float
    #: Buckets that had nothing in them before and have something now.
    newly_used: tuple[str, ...] = ()

    @property
    def delta(self) -> float:
        return self.now - self.was

    @property
    def widened(self) -> bool:
        return self.delta > 0.0 or bool(self.newly_used)


def diff(before: Profile, after: Profile) -> list[Movement]:
    """Every dimension that moved, widest first. Empty when nothing changed —
    which is a real answer and is reported as one."""
    moved = []
    for dim_id, later in after.dimensions.items():
        earlier = before.dimensions.get(dim_id)
        if earlier is None:
            continue
        fresh = tuple(b for b in later.counts if b not in earlier.counts)
        movement = Movement(
            dimension=later.dimension,
            was=earlier.exploration,
            now=later.exploration,
            newly_used=fresh,
        )
        if abs(movement.delta) > 1e-9 or fresh:
            moved.append(movement)
    return sorted(moved, key=lambda m: (-m.delta, m.dimension.id))


# --- from a tendency to something to do -----------------------------------------

#: Which techniques push against a dimension's dominant bucket. This is the
#: whole bridge from "you always do X" to "here is something to try": the Scout
#: still chooses from the skill graph and its prerequisites, but a technique
#: named here is preferred when the profile has something to say. Ids are
#: checked against the catalogue by a test, so a rename cannot rot this quietly.
PUSHES_AGAINST: dict[tuple[str, str], tuple[str, ...]] = {
    ("placement", "centred"): ("rule_of_thirds", "negative_space", "rule_of_odds"),
    ("placement", "off centre"): ("centre_composition", "symmetry"),
    ("placement", "near the edge"): ("centre_composition", "fill_the_frame"),
    ("framing", "wide"): ("fill_the_frame", "macro", "eye_contact_portrait"),
    ("framing", "medium"): ("fill_the_frame", "negative_space"),
    ("framing", "close"): ("negative_space", "layering", "wide_angle"),
    ("light", "open day"): ("golden_hour", "blue_hour", "backlight"),
    ("light", "golden hour"): ("hard_light", "window_light"),
    ("light", "blue hour"): ("golden_hour", "hard_light"),
    ("light", "night"): ("golden_hour", "window_light"),
    ("key", "low key"): ("high_key", "soft_light"),
    ("key", "mid key"): ("low_key", "high_key", "chiaroscuro"),
    ("key", "high key"): ("low_key", "chiaroscuro"),
    ("palette", "warm"): ("monochrome", "muted_palette", "complementary"),
    ("palette", "neutral"): ("single_accent", "colour_blocking"),
    ("palette", "cool"): ("warm_cool", "single_accent"),
    ("orientation", "landscape"): ("negative_space", "eye_contact_portrait"),
    ("orientation", "portrait"): ("layering", "patterns"),
    ("orientation", "square"): ("layering", "leading_lines"),
    ("height", "eye level"): ("low_angle", "high_angle"),
    ("height", "low"): ("high_angle", "eye_contact_portrait"),
    ("height", "high"): ("low_angle", "eye_contact_portrait"),
}

#: What to try when the photographer takes one frame and walks on. Working the
#: scene is not a technique in the catalogue, so the challenge is carried by the
#: sentence rather than by an id.
DWELL_SUGGESTS: tuple[str, ...] = ("fill_the_frame", "low_angle", "negative_space")


@dataclass(frozen=True)
class Challenge:
    """One thing to try, and the counts that earned it.

    The citation is the point. A challenge that cannot name the arithmetic
    behind it is generic advice, which is the tier this product exists to rise
    above — so this carries the sentence, and the Scout is required to show it
    on the card rather than paraphrase it away.
    """

    #: What the photographer reads: "13 of 18 frames are warm".
    citation: str
    #: Techniques that would push against the tendency, best first.
    prefers: tuple[str, ...]
    #: The dimension this came from, or "dwell".
    source: str

    def __bool__(self) -> bool:
        return bool(self.citation)


def challenge_for(profile: Profile) -> Challenge | None:
    """What the profile suggests trying next, or nothing.

    Nothing is a real answer: a photographer whose work is spread across every
    dimension has no tendency worth naming, and inventing one to fill a card is
    exactly the generic advice this refuses to give.
    """
    if profile.dwell.walks_on:
        dwell = profile.dwell
        return Challenge(
            citation=(
                f"{dwell.shots} shots across {dwell.scenes} scenes — "
                f"{dwell.per_scene:.1f} frames before you move on"
            ),
            prefers=DWELL_SUGGESTS,
            source="dwell",
        )

    narrowest = profile.narrowest()
    if narrowest is None:
        return None
    bucket = narrowest.dominant
    count = narrowest.counts.get(bucket, 0)
    citation = f"{count} of {narrowest.n} readable shots: {bucket}"
    if narrowest.unexplored:
        citation += f" — never {', '.join(narrowest.unexplored)}"
    return Challenge(
        citation=citation,
        prefers=PUSHES_AGAINST.get((narrowest.dimension.id, bucket), ()),
        source=narrowest.dimension.id,
    )
