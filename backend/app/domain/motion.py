"""Camera-move arithmetic: what the measured drift implies. Pure.

``imaging/motion.py`` measures how the framing travelled between consecutive
frames. This says what that means, and — more usefully — what it rules out.

The video family was the worst-served in the panel: twelve techniques firing at
0.11 sightings a shot against composition's 1.94, because they were being read
off a contact sheet whose tiles are seconds apart. A pan, a tracking shot and a
cut are indistinguishable across that gap. Three real clips measured here come
apart cleanly: 2.42 frame widths of travel with 5% of steps still, 0.58 with
53% still, and 0.03 with 92% still.

What translation cannot settle it does not claim. ``orbit``, ``push_in``,
``tracking`` and ``rack_focus`` all involve rotation, scale or focus rather
than a shift of the frame, so nothing here corroborates them and the lenses
keep the last word. ``static_tripod``, ``pan``, ``tilt`` and ``whip_pan`` are
statements about translation, and those this can prove or disprove.
"""

from dataclasses import dataclass

from app.domain.entities import Motion

STATIC_TRIPOD = "static_tripod"
PAN = "pan"
TILT = "tilt"
WHIP_PAN = "whip_pan"

#: The techniques this module can speak to at all. A lens claiming anything
#: else gets no help and no contradiction from here.
SETTLED: frozenset[str] = frozenset({STATIC_TRIPOD, PAN, TILT, WHIP_PAN})

#: Share of steps with no measurable movement before the camera counts as
#: locked off. The corpus splits 0.92 / 0.53 / 0.05, so 0.75 takes the tripod
#: and leaves the slow pan alone.
STILL_SHARE = 0.75
#: Total travel, in frame widths, before a drift is a move rather than a hand
#: not quite holding still. The slow deliberate pan in the corpus is 0.58 and
#: the locked-off clip is 0.03; 0.25 separates them with room on both sides.
MOVE_DRIFT = 0.25
#: How much one axis must beat the other to name the move pan or tilt rather
#: than a diagonal drift.
AXIS_RATIO = 2.0
#: Frame widths in a single 1/4 s step before the frames smear. A whip pan is
#: not a fast pan: the corpus pan peaks at 0.063 a step and the fast one at
#: 0.634, an order of magnitude apart.
WHIP_STEP = 0.25


@dataclass(frozen=True)
class Read:
    """What the drift says. ``move`` is empty when nothing is settled."""

    move: str
    #: Techniques the measurement supports and contradicts, both from SETTLED.
    supports: frozenset[str]
    contradicts: frozenset[str]
    #: The sentence a lens or the Judge is given.
    fact: str


def _direction(motion: Motion) -> str:
    if abs(motion.drift_x) * AXIS_RATIO > abs(motion.drift_y):
        return "right" if motion.drift_x > 0 else "left"
    return "down" if motion.drift_y > 0 else "up"


def read(motion: Motion | None) -> Read:
    """Classify one clip's camera movement."""
    if motion is None or motion.frames < 2:
        return Read(move="", supports=frozenset(), contradicts=frozenset(), fact="")

    travel = max(abs(motion.drift_x), abs(motion.drift_y))
    seconds = motion.frames / motion.fps if motion.fps else 0.0
    where = _direction(motion)

    if motion.still_share >= STILL_SHARE and travel < MOVE_DRIFT:
        return Read(
            move=STATIC_TRIPOD,
            supports=frozenset({STATIC_TRIPOD}),
            contradicts=SETTLED - {STATIC_TRIPOD},
            fact=f"the framing is locked: {motion.still_share:.0%} of steps show no movement "
            f"and total travel is {travel:.2f} frame widths over {seconds:.0f} s",
        )

    if travel < MOVE_DRIFT:
        return Read(
            move="",
            supports=frozenset(),
            contradicts=frozenset({PAN, TILT, WHIP_PAN}),
            fact=f"the camera barely travels: {travel:.2f} frame widths total, "
            f"below the {MOVE_DRIFT} that would make this a move",
        )

    if motion.step_max >= WHIP_STEP:
        return Read(
            move=WHIP_PAN,
            supports=frozenset({WHIP_PAN, PAN}),
            contradicts=frozenset({STATIC_TRIPOD}),
            fact=f"one step moves {motion.step_max:.2f} of the frame width — fast enough to "
            f"smear; the clip travels {travel:.2f} frame widths {where} over {seconds:.0f} s",
        )

    horizontal = abs(motion.drift_x) > abs(motion.drift_y) * AXIS_RATIO
    vertical = abs(motion.drift_y) > abs(motion.drift_x) * AXIS_RATIO
    move = PAN if horizontal else TILT if vertical else ""
    supports = frozenset({move}) if move else frozenset()
    contradicts = frozenset({STATIC_TRIPOD, WHIP_PAN}) | (
        {TILT} if horizontal else {PAN} if vertical else set()
    )
    shape = "a pan" if horizontal else "a tilt" if vertical else "a diagonal drift"
    return Read(
        move=move,
        supports=supports,
        contradicts=contradicts,
        fact=f"{shape} {where}: {travel:.2f} frame widths over {seconds:.0f} s, "
        f"{motion.step:.1%} of the frame per step, {motion.reversals} direction "
        f"{'reversal' if motion.reversals == 1 else 'reversals'}",
    )


def describe(motion: Motion | None) -> list[str]:
    """Plain lines for prompts, in the shape ``exposure.describe`` returns."""
    found = read(motion)
    if not found.fact:
        return []
    lines = [found.fact]
    if found.contradicts:
        lines.append("measured translation rules out: " + ", ".join(sorted(found.contradicts)))
    lines.append(
        "rotation, scale and focus are not measured, so orbit, push_in, tracking and "
        "rack_focus are yours to judge from the frames"
    )
    return lines
