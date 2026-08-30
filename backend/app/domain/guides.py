"""Which compositional guide to draw over a frame, for a human.

Two different grids serve two different readers. The cell grid (`A1`..`G9`)
is an addressing system: it exists so a model can point at things and so code
can map that back to pixels. It is not a compositional idea and showing it to
a photographer teaches nothing.

What a photographer reads is a guide — thirds, the phi grid, the diagonal
method, a centre axis — and what they want to know is whether the frame is
sitting on it. So the guide is chosen from the strongest retained spatial
Technique, and the app draws that one, not the mesh.

Pure. The renderers (SVG in the browser, PIL for the Drive review) own the
geometry; this owns only the choice.
"""

from app.domain.entities import TechniqueEvidence

#: Guide ids the renderers know how to draw.
THIRDS = "thirds"
CENTRE = "centre"
DIAGONALS = "diagonals"
FILL = "fill"
PHI = "phi"
NONE = "none"

GUIDES = (THIRDS, CENTRE, DIAGONALS, FILL, PHI, NONE)

#: Only composition techniques choose a guide; light and colour have no
#: geometry to draw. A technique missing here simply does not vote.
BY_TECHNIQUE = {
    "rule_of_thirds": THIRDS,
    "rule_of_odds": THIRDS,
    "horizon_placement": THIRDS,
    "negative_space": THIRDS,
    "centre_composition": CENTRE,
    "symmetry": CENTRE,
    "reflections": CENTRE,
    "leading_lines": DIAGONALS,
    "diagonals": DIAGONALS,
    "layering": DIAGONALS,
    "fill_the_frame": FILL,
    "minimalism": THIRDS,
}

#: With no retained spatial Technique, thirds is the guide every photographer already
#: has in their head — drawn dimmed, as a reference rather than a claim.
FALLBACK = THIRDS

#: The two grids a subject can be placed on, as fractions of the frame. They sit
#: 0.049 apart, which no lens can tell apart by eye — so the choice between them
#: is measured here from the point the Composer gave, not asked of a model.
THIRDS_LINES: tuple[float, ...] = (1 / 3, 2 / 3)
PHI_LINES: tuple[float, ...] = (0.382, 0.618)


def _distance(position: float, lines: tuple[float, ...]) -> float:
    return min(abs(line - position) for line in lines)


def refine(guide: str, subject_x: float | None, subject_y: float | None) -> str:
    """Thirds or phi, decided by where the subject actually is.

    Only the thirds guide is refined. A frame the panel read as centred or
    diagonal is not a placement question, and redrawing it on a phi grid would
    answer something nobody asked."""
    if guide != THIRDS:
        return guide
    positions = [value for value in (subject_x, subject_y) if value is not None]
    if not positions:
        return guide
    thirds = min(_distance(value, THIRDS_LINES) for value in positions)
    phi = min(_distance(value, PHI_LINES) for value in positions)
    return PHI if phi < thirds else THIRDS


def choose(
    techniques: list[TechniqueEvidence],
    subject_x: float | None = None,
    subject_y: float | None = None,
) -> str:
    """The guide for the strongest retained spatial Technique,
    refined to the grid the subject is actually nearer."""
    best: tuple[float, str] | None = None
    for evidence in techniques:
        guide = BY_TECHNIQUE.get(evidence.technique_id)
        if guide is None:
            continue
        if best is None or evidence.confidence > best[0]:
            best = (evidence.confidence, guide)
    return refine(best[1] if best else FALLBACK, subject_x, subject_y)
