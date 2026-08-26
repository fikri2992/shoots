"""Cartographer rules and evidence-backed Scout selection."""

from datetime import UTC, datetime, timedelta

from app.domain import scout
from app.domain import technique_map as tmap
from app.domain.entities import Analysis, TechniqueEvidence, TechniqueState, TechniqueStatus

T0 = datetime(2026, 8, 22, tzinfo=UTC)


def analysis(shot: str, *evidence: tuple) -> Analysis:
    """``(technique_id, confidence)`` or ``(technique_id, confidence, agreement)``.

    Agreement defaults to two lenses, the ordinary case for evidence that
    passed the panel; the tests that turn on it say so explicitly.
    """
    return Analysis(
        shot_id=shot,
        user_id="u",
        model="m",
        techniques=[
            TechniqueEvidence(
                technique_id=e[0], confidence=e[1], agreement=e[2] if len(e) > 2 else 2
            )
            for e in evidence
        ],
    )


def test_low_confidence_evidence_does_not_count():
    graph: dict[str, TechniqueState] = {}
    changed = tmap.apply_analysis(graph, analysis("s1", ("panning", 0.59)), T0)
    assert changed == [] and graph == {}


def test_climb_observed_to_recurring():
    graph: dict[str, TechniqueState] = {}
    tmap.apply_analysis(graph, analysis("s1", ("panning", 0.9)), T0)
    assert graph["panning"].status is TechniqueStatus.OBSERVED
    tmap.apply_analysis(graph, analysis("s2", ("panning", 0.9)), T0 + timedelta(days=1))
    assert graph["panning"].status is TechniqueStatus.OBSERVED
    tmap.apply_analysis(graph, analysis("s3", ("panning", 0.9)), T0 + timedelta(days=2))
    state = graph["panning"]
    assert state.status is TechniqueStatus.RECURRING
    assert state.attempts == 3 and state.corroborated == 3
    assert "best_score" not in state.model_dump() and "last_score" not in state.model_dump()
    assert state.shot_ids == ["s1", "s2", "s3"]


def test_same_shot_twice_is_a_noop():
    graph: dict[str, TechniqueState] = {}
    tmap.apply_analysis(graph, analysis("s1", ("panning", 0.9)), T0)
    assert tmap.apply_analysis(graph, analysis("s1", ("panning", 0.9)), T0) == []
    assert graph["panning"].attempts == 1


def test_one_uncorroborated_sighting_keeps_recurring_from_forming():
    """Three sightings, but the middle one was a single lens. Solid asks for
    three corroborated, so it stays practiced until a third one arrives."""
    graph: dict[str, TechniqueState] = {}
    for i, agreement in enumerate([2, 1, 2]):
        tmap.apply_analysis(graph, analysis(f"s{i}", ("panning", 0.9, agreement)), T0)
    state = graph["panning"]
    assert state.attempts == 3 and state.corroborated == 2
    assert state.status is TechniqueStatus.OBSERVED
    tmap.apply_analysis(graph, analysis("s3", ("panning", 0.9)), T0)
    assert graph["panning"].status is TechniqueStatus.RECURRING


def test_one_lens_repeating_itself_never_recurs():
    """The panel lets a single lens through at 0.75 and above, so a lens with a
    Tendency can carry a Technique on its own indefinitely. Repetition is not
    corroboration, and the map must not read it as recurrence."""
    graph: dict[str, TechniqueState] = {}
    for i in range(8):
        tmap.apply_analysis(graph, analysis(f"s{i}", ("panning", 0.95, 1)), T0)
    state = graph["panning"]
    assert state.attempts == 8 and state.corroborated == 0
    assert state.status is TechniqueStatus.OBSERVED


def test_each_technique_moves_only_from_its_own_evidence():
    graph: dict[str, TechniqueState] = {}
    for i in range(3):
        tmap.apply_analysis(
            graph,
            analysis(
                f"s{i}",
                ("panning", 0.9, 2),
                ("golden_hour", 0.9, 1),
                ("leading_lines", 0.9, 2),
            ),
            T0 + timedelta(days=i),
        )
    assert all("best_score" not in state.model_dump() for state in graph.values())
    assert graph["panning"].status is TechniqueStatus.RECURRING
    assert graph["leading_lines"].status is TechniqueStatus.RECURRING
    assert graph["golden_hour"].status is TechniqueStatus.OBSERVED


def test_confident_but_alone_is_not_corroborated():
    assert not tmap.corroborated(TechniqueEvidence(technique_id="x", confidence=1.0, agreement=1))
    assert not tmap.corroborated(TechniqueEvidence(technique_id="x", confidence=0.7, agreement=3))
    assert tmap.corroborated(TechniqueEvidence(technique_id="x", confidence=0.75, agreement=2))


def test_what_recurred_keeps_having_recurred():
    """The record used to expire into `rusty`, which told the photographer they
    had got worse at something when all that had happened was time. It
    recurred; a month of rain does not make that untrue (decision 46)."""
    graph: dict[str, TechniqueState] = {}
    for i in range(3):
        tmap.apply_analysis(graph, analysis(f"s{i}", ("panning", 0.9)), T0)
    assert graph["panning"].status is TechniqueStatus.RECURRING

    tmap.apply_analysis(graph, analysis("s3", ("panning", 0.9)), T0 + timedelta(days=30))
    assert graph["panning"].status is TechniqueStatus.RECURRING


def test_shot_memory_is_capped():
    graph: dict[str, TechniqueState] = {}
    for i in range(15):
        tmap.apply_analysis(graph, analysis(f"s{i}", ("panning", 0.9)), T0)
    assert len(graph["panning"].shot_ids) == tmap.SHOT_MEMORY
    assert graph["panning"].attempts == 15


# --- scout ----------------------------------------------------------------


def test_scout_uses_only_the_evidenced_direction_and_skips_recent():
    first = scout.choose(("rule_of_thirds", "negative_space"), [])
    second = scout.choose(("rule_of_thirds", "negative_space"), ["rule_of_thirds"])
    assert first is not None and first.id == "rule_of_thirds"
    assert second is not None and second.id == "negative_space"


def test_scout_stays_silent_without_a_supported_direction():
    assert scout.choose((), []) is None
    assert scout.choose(("rule_of_thirds",), ["rule_of_thirds"]) is None


def test_direction_is_not_gated_by_prerequisite_levels():
    selected = scout.choose(("rim_light",), [])
    assert selected is not None and selected.id == "rim_light"


def test_video_direction_needs_a_video_context():
    assert scout.choose(("pan",), []) is None
    assert scout.choose(("pan",), [], video=True).id == "pan"
