"""Three lenses, one verdict on what the frame shows. Pure.

A single model reading a frame is one opinion with one set of blind spots.
Shoots reads every frame with a panel of three lenses that differ in what
they are asked and what they are shown (``agents/analyst.py``):

    technician   exposure, lens, technical excellence     sees EXIF + the gridded frame
    composer     composition, light, cells, moves          sees the gridded frame only
    storyteller  impact, story, colour, the human read     sees the clean frame only

This module is the vote. A technique is evidence when at least two lenses
saw it, or when the lens that owns its family saw it with high confidence;
its confidence is the mean over the lenses that agreed. Element scores are
averaged over the lenses that rate them. Panels of diverse graders beat a
single grader only when their errors are not shared, which is why the
lenses see different things; a panel below quorum is not a reading at all
and the stage retries.

**Arithmetic outranks the panel.** ``aggregate`` takes two sets of technique
ids that measurement has already settled, and they are not advisory: a
technique in ``settled_against`` loses its evidence however many lenses saw
it and however sure they were, and one in ``settled_for`` needs only a single
lens to have noticed it, because the corroboration came from outside the
model. The sets arrive as plain ids — this module does not need to know which
measurement settled them, only that one did (``domain/motion.py`` supplies
them today for camera movement; ``domain/tone.py`` and ``domain/exposure.py``
could supply more).

Until this existed the measurement reached the lens *prompts* and stopped
there, so a lens could vote ``static_tripod`` on a clip measured at 2.42
frame widths of travel and the evidence stood. "Arithmetic, not opinion" was
true of the prompts and false of the panel.
"""

from dataclasses import dataclass, field

from app.domain import rubric, taxonomy
from app.domain.entities import TechniqueEvidence
from app.domain.taxonomy import Family

TECHNICIAN = "technician"
COMPOSER = "composer"
STORYTELLER = "storyteller"
#: Video only: two exact frames compared (agents/scrub.py). Votes, rates nothing.
SCRUB = "scrub"
LENSES: tuple[str, ...] = (TECHNICIAN, COMPOSER, STORYTELLER, SCRUB)
#: The lenses that always run; the scrub joins for video.
PANEL: tuple[str, ...] = (TECHNICIAN, COMPOSER, STORYTELLER)

#: Not a lens: the name arithmetic votes under, recorded in ``Evidence.lenses``
#: so the corroboration is visible on the frame page and in the feed. It is
#: listed apart from ``LENSES`` because it rates no elements and writes no
#: observations — it only settles what it can settle.
MEASURED = "measured"
#: The confidence a measured technique carries. One, and not a blend with the
#: lens's own number: ``domain/motion.py`` says of its settled set that it can
#: "prove or disprove" them, and a proof does not get less certain because a
#: model was only half sure. This is also what carries the sighting past the
#: Technique Map's corroboration bar (decision 33), which is correct — arithmetic
#: is the one voter in the system that cannot share the panel's blind spots.
MEASURED_CONFIDENCE = 1.0

#: Which lens's word counts alone (with high confidence) for a family.
OWNER_BY_FAMILY: dict[Family, str] = {
    Family.EXPOSURE: TECHNICIAN,
    Family.LENS: TECHNICIAN,
    Family.COMPOSITION: COMPOSER,
    Family.LIGHT: COMPOSER,
    Family.VIDEO: COMPOSER,
    Family.COLOR: STORYTELLER,
}
#: Frame-rate and time-span techniques are read off ffprobe, not the frames.
OWNER_OVERRIDES: dict[str, str] = {"slow_motion": TECHNICIAN, "timelapse": TECHNICIAN}

#: Which rubric elements each lens rates. Anything else it returns is dropped.
LENS_ELEMENTS: dict[str, tuple[str, ...]] = {
    TECHNICIAN: ("technical",),
    COMPOSER: ("composition", "lighting"),
    STORYTELLER: ("impact", "story"),
    SCRUB: (),
}

MAX_OBSERVATIONS = 12


def owner_of(technique_id: str) -> str:
    if technique_id in OWNER_OVERRIDES:
        return OWNER_OVERRIDES[technique_id]
    return OWNER_BY_FAMILY[taxonomy.BY_ID[technique_id].family]


@dataclass(frozen=True)
class Sighting:
    technique_id: str
    confidence: float
    cells: tuple[str, ...] = ()
    note: str = ""


@dataclass
class LensRead:
    """One lens's validated output: ids and cells already checked."""

    lens: str
    sightings: list[Sighting] = field(default_factory=list)
    elements: dict[str, int] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)


@dataclass
class Consensus:
    techniques: list[TechniqueEvidence]
    elements: dict[str, int]
    observations: list[str]
    quorum: int
    #: Sightings that did not make it, for the feed: (lens, technique, confidence).
    dissent: list[tuple[str, str, float]]
    #: Why the panel could not call this frame, or empty when it could.
    #:
    #: Expertise includes knowing the edge of your own competence. Three lenses
    #: that each saw something different have not produced a reading; they have
    #: produced three opinions, and averaging them into a verdict manufactures
    #: a confidence nobody had. The photographer is a hobbyist who cannot audit
    #: a critic, so an honest "I could not call this one" is worth more to them
    #: than a fluent answer that happens to be arbitrary.
    #:
    #: Findings are unaffected: they are arithmetic, and stay true whatever the
    #: lenses disagreed about.
    abstained: str = ""

    @property
    def confident(self) -> bool:
        return not self.abstained


def aggregate(
    reads: list[LensRead],
    min_confidence: float = 0.4,
    min_agreement: int = 2,
    owner_confidence: float = 0.75,
    quorum: int = 2,
    settled_for: frozenset[str] = frozenset(),
    settled_against: frozenset[str] = frozenset(),
) -> Consensus:
    """The panel's verdict, with measurement given the last word.

    ``settled_for`` and ``settled_against`` are technique ids that arithmetic
    has already decided (``domain/motion.py`` read()). Against is a veto and
    outranks every lens; for is a corroborating vote, so one lens noticing is
    enough. A technique arithmetic settles *for* that no lens mentioned at all
    stays out: evidence is still a claim a lens made, and a measurement with
    no reading behind it is a gap in the panel rather than a sighting.
    """
    if len(reads) < quorum:
        raise ValueError(f"panel quorum not met: {len(reads)} of {quorum} lenses answered")

    by_lens = {read.lens: read for read in reads}
    order = [lens for lens in LENSES if lens in by_lens]

    # technique -> lens -> sighting, only sightings above the per-lens floor
    votes: dict[str, dict[str, Sighting]] = {}
    for lens in order:
        for s in by_lens[lens].sightings:
            if s.confidence >= min_confidence:
                votes.setdefault(s.technique_id, {})[lens] = s

    techniques: list[TechniqueEvidence] = []
    dissent: list[tuple[str, str, float]] = []
    for tid, lens_votes in votes.items():
        # The veto. A measurement that rules a technique out ends the matter,
        # whoever saw it and however sure they were; the sighting still travels
        # as dissent so the feed shows what the lens said and why it lost.
        if tid in settled_against:
            dissent.extend((lens, tid, s.confidence) for lens, s in lens_votes.items())
            continue
        owner = owner_of(tid)
        owner_sighting = lens_votes.get(owner)
        measured = tid in settled_for
        agreed = len(lens_votes) + measured >= min_agreement
        trusted_owner = owner_sighting is not None and owner_sighting.confidence >= owner_confidence
        if not (agreed or trusted_owner or measured):
            dissent.extend((lens, tid, s.confidence) for lens, s in lens_votes.items())
            continue
        lenses = [lens for lens in order if lens in lens_votes]
        confidence = sum(lens_votes[lens].confidence for lens in lenses) / len(lenses)
        cells: list[str] = []
        for lens in ([owner] if owner in lens_votes else []) + [
            lens for lens in lenses if lens != owner
        ]:
            for cell in lens_votes[lens].cells:
                if cell not in cells:
                    cells.append(cell)
        note_source = owner_sighting or lens_votes[lenses[0]]
        # Cells and the note come from the lenses that looked; the measurement
        # joins the vote afterwards, having none of either.
        if measured:
            lenses = [*lenses, MEASURED]
            confidence = MEASURED_CONFIDENCE
        techniques.append(
            TechniqueEvidence(
                technique_id=tid,
                confidence=round(min(1.0, confidence), 3),
                cells=cells,
                note=note_source.note,
                agreement=len(lenses),
                lenses=lenses,
            )
        )
    techniques.sort(key=lambda t: (-t.agreement, -t.confidence, t.technique_id))

    elements: dict[str, int] = {}
    for element in rubric.ELEMENTS:
        scores = [
            rubric.clamp(by_lens[lens].elements[element])
            for lens in order
            if element in LENS_ELEMENTS[lens] and element in by_lens[lens].elements
        ]
        if scores:
            elements[element] = rubric.clamp(round(sum(scores) / len(scores)))

    observations: list[str] = []
    seen: set[str] = set()
    for lens in order:
        for line in by_lens[lens].observations:
            text = " ".join(line.split()).strip()
            if text and text.lower() not in seen:
                seen.add(text.lower())
                observations.append(text)
    return Consensus(
        techniques=techniques,
        elements=elements,
        observations=observations[:MAX_OBSERVATIONS],
        quorum=len(reads),
        dissent=dissent,
        abstained=_abstention(techniques, dissent, len(reads)),
    )


#: How many rejected sightings make a disagreement rather than a quiet frame.
CONTESTED_SIGHTINGS = 3


def _abstention(
    techniques: list[TechniqueEvidence],
    dissent: list[tuple[str, str, float]],
    quorum: int,
) -> str:
    """Whether this reading is worth stating, and if not, why.

    Two different silences have to be told apart. A frame where the lenses
    simply had little to say is quiet, and a quiet frame is a fine thing to
    report. A frame where every lens saw something and no two of them saw the
    same thing is *contested*, and that is not a reading at all — it is three
    opinions in a room. Only the second abstains.
    """
    if techniques:
        return ""
    lenses_that_claimed = {lens for lens, _, _ in dissent}
    if len(dissent) >= CONTESTED_SIGHTINGS and len(lenses_that_claimed) >= quorum:
        return (
            f"{len(lenses_that_claimed)} lenses each saw something and no two agreed "
            f"({len(dissent)} sightings, none corroborated)"
        )
    return ""
