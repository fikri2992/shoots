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
"""

from dataclasses import dataclass, field

from app.domain import rubric, taxonomy
from app.domain.entities import TechniqueEvidence
from app.domain.taxonomy import Family

TECHNICIAN = "technician"
COMPOSER = "composer"
STORYTELLER = "storyteller"
LENSES: tuple[str, ...] = (TECHNICIAN, COMPOSER, STORYTELLER)

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


def aggregate(
    reads: list[LensRead],
    min_confidence: float = 0.4,
    min_agreement: int = 2,
    owner_confidence: float = 0.75,
    quorum: int = 2,
) -> Consensus:
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
        owner = owner_of(tid)
        owner_sighting = lens_votes.get(owner)
        agreed = len(lens_votes) >= min_agreement
        trusted_owner = owner_sighting is not None and owner_sighting.confidence >= owner_confidence
        if not (agreed or trusted_owner):
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
    )
