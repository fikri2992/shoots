"""Which compositional guide to draw over a frame, for a human.

Two different grids serve two different readers. The cell grid (`A1`..`G9`)
is an addressing system: it exists so a model can point at things and so code
can map that back to pixels. It is not a compositional idea and showing it to
a photographer teaches nothing.

What a photographer reads is a guide — thirds, the phi grid, the diagonal
method, a centre axis — and what they want to know is whether the frame is
sitting on it. So the guide is chosen from the technique the panel actually
agreed the frame is built on, and the app draws that one, not the mesh.

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

#: With nothing spatial agreed, thirds is the guide every photographer already
#: has in their head — drawn dimmed, as a reference rather than a claim.
FALLBACK = THIRDS


def choose(techniques: list[TechniqueEvidence]) -> str:
    """The guide for the strongest spatial technique the panel agreed on."""
    best: tuple[float, str] | None = None
    for evidence in techniques:
        guide = BY_TECHNIQUE.get(evidence.technique_id)
        if guide is None:
            continue
        if best is None or evidence.confidence > best[0]:
            best = (evidence.confidence, guide)
    return best[1] if best else FALLBACK
