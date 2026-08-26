"""Select a Technique only from an evidenced Experiment Direction."""

from app.domain import taxonomy
from app.domain.taxonomy import Technique


def available(
    technique: Technique,
    *,
    video: bool = False,
    missing_gear: tuple[str, ...] | list[str] = (),
) -> bool:
    """Whether known constraints permit this Technique right now."""
    return (video or not technique.video_only) and not (set(technique.needs) & set(missing_gear))


def choose(
    preferred_ids: tuple[str, ...] | list[str],
    recent_technique_ids: list[str],
    *,
    video: bool = False,
    missing_gear: tuple[str, ...] | list[str] = (),
) -> Technique | None:
    """First supported direction not recently offered, or honest silence."""
    recent = set(recent_technique_ids)
    for technique_id in preferred_ids:
        technique = taxonomy.BY_ID.get(technique_id)
        if technique is None or technique.id in recent:
            continue
        if available(technique, video=video, missing_gear=missing_gear):
            return technique
    return None


def why_now(technique: Technique, citation: str) -> str:
    """The evidence-backed reason shown on the Experiment card."""
    return f"Your own Shots show {citation}. Try {technique.name} to explore another decision."
