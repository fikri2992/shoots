"""The scoring rubric: five elements, anchored, weighted, computed.

Derived from the Professional Photographers of America's *12 Elements of a
Merit Image* (the judging standard for PPA print competitions), reduced to
the elements that apply to an unedited single frame from a learner:
Presentation, Style and Technique are about finished competition prints.
Center of Interest folds into Composition; Subject Matter and Creativity
into Story; Color Balance into Technical. Impact sits at the centre of
PPA's model, so it carries the most weight here.

PPA scores 100 points in bands (95-100 exceptional, 80-84 merit, 70-74
average, below 70 not exhibition standard). Ours is 1-10 per element with
the same bands as anchors, so a lens rates against a described level, not
a feeling; anchored descriptors are what keeps model graders consistent.
The overall score is a weighted mean computed here, never asserted by a
model.
"""

ELEMENTS: tuple[str, ...] = ("impact", "composition", "lighting", "technical", "story")

WEIGHTS: dict[str, float] = {
    "impact": 0.30,
    "composition": 0.25,
    "lighting": 0.20,
    "technical": 0.15,
    "story": 0.10,
}

#: What each element asks, in the judges' words, for the prompts.
QUESTIONS: dict[str, str] = {
    "impact": "Does the frame evoke a feeling at first sight: surprise, warmth, tension, calm?",
    "composition": "Do the visual elements come together to express one intent, with a clear "
    "centre of interest and nothing pulling against it?",
    "lighting": "Is light used and controlled: does it model shape, set the mood, separate "
    "subject from ground?",
    "technical": "Exposure, focus where it matters, sharpness, colour balance, noise: is the "
    "frame clean enough that nothing technical distracts?",
    "story": "Does the subject matter and the moment say something; does it leave the viewer "
    "with a thought or a question?",
}

#: Score anchors shared by every lens. Mapped from PPA's 100-point bands.
ANCHORS: dict[int, str] = {
    10: "exceptional: a reference image for this element; nothing to change",
    9: "superior: a working professional would be pleased with this element",
    8: "merit: clearly above a competent photographer's everyday work",
    7: "above average: the element is handled with intent and mostly succeeds",
    6: "average: competent, nothing wrong, nothing memorable",
    5: "below average: one clear weakness in this element",
    4: "weak: the element works against the frame",
    3: "poor: the element is mostly absent or mishandled",
    2: "very poor",
    1: "failed: the element makes the frame unreadable",
}

BANDS: tuple[tuple[int, str], ...] = (
    (9, "exceptional"),
    (8, "merit"),
    (7, "above average"),
    (6, "average"),
    (1, "below standard"),
)


def anchors_text() -> str:
    return "\n".join(f"- {score}: {text}" for score, text in sorted(ANCHORS.items(), reverse=True))


def clamp(value: int) -> int:
    return max(1, min(10, int(value)))


def overall(elements: dict[str, int]) -> int:
    """Weighted mean over the elements present; weights renormalised so a
    missing element (a lens that failed) does not drag the score down."""
    present = {k: clamp(v) for k, v in elements.items() if k in WEIGHTS}
    if not present:
        return 5
    total_weight = sum(WEIGHTS[k] for k in present)
    score = sum(WEIGHTS[k] * v for k, v in present.items()) / total_weight
    return clamp(round(score))


def band(score: int) -> str:
    for floor, label in BANDS:
        if score >= floor:
            return label
    return "below standard"
