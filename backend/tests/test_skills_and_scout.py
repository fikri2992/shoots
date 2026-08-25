"""Cartographer rules and Scout ranking. Pure, exhaustive where cheap."""

from datetime import UTC, datetime, timedelta

from app.domain import scout, skills
from app.domain.entities import Analysis, SkillState, SkillStatus, TechniqueEvidence

T0 = datetime(2026, 8, 22, tzinfo=UTC)


def analysis(shot: str, score: int, *evidence: tuple) -> Analysis:
    """``(technique_id, confidence)`` or ``(technique_id, confidence, agreement)``.

    Agreement defaults to two lenses, the ordinary case for evidence that
    passed the panel; the tests that turn on it say so explicitly.
    """
    return Analysis(
        shot_id=shot,
        user_id="u",
        model="m",
        score=score,
        techniques=[
            TechniqueEvidence(
                technique_id=e[0], confidence=e[1], agreement=e[2] if len(e) > 2 else 2
            )
            for e in evidence
        ],
    )


def test_low_confidence_evidence_does_not_count():
    graph: dict[str, SkillState] = {}
    changed = skills.apply_analysis(graph, analysis("s1", 6, ("panning", 0.59)), T0)
    assert changed == [] and graph == {}


def test_climb_attempted_practiced_solid():
    graph: dict[str, SkillState] = {}
    skills.apply_analysis(graph, analysis("s1", 4, ("panning", 0.9)), T0)
    assert graph["panning"].status is SkillStatus.ATTEMPTED
    skills.apply_analysis(graph, analysis("s2", 6, ("panning", 0.9)), T0 + timedelta(days=1))
    assert graph["panning"].status is SkillStatus.PRACTICED
    skills.apply_analysis(graph, analysis("s3", 8, ("panning", 0.9)), T0 + timedelta(days=2))
    state = graph["panning"]
    assert state.status is SkillStatus.SOLID
    assert state.attempts == 3 and state.best_score == 8 and state.last_score == 8
    assert state.shot_ids == ["s1", "s2", "s3"]


def test_same_shot_twice_is_a_noop():
    graph: dict[str, SkillState] = {}
    skills.apply_analysis(graph, analysis("s1", 7, ("panning", 0.9)), T0)
    assert skills.apply_analysis(graph, analysis("s1", 7, ("panning", 0.9)), T0) == []
    assert graph["panning"].attempts == 1


def test_one_uncorroborated_sighting_keeps_solid_from_forming():
    """Three sightings, but the middle one was a single lens. Solid asks for
    three corroborated, so it stays practiced until a third one arrives."""
    graph: dict[str, SkillState] = {}
    for i, agreement in enumerate([2, 1, 2]):
        skills.apply_analysis(graph, analysis(f"s{i}", 8, ("panning", 0.9, agreement)), T0)
    state = graph["panning"]
    assert state.attempts == 3 and state.corroborated == 2
    assert state.status is SkillStatus.PRACTICED
    skills.apply_analysis(graph, analysis("s3", 8, ("panning", 0.9)), T0)
    assert graph["panning"].status is SkillStatus.SOLID


def test_one_lens_repeating_itself_never_reaches_solid():
    """The panel lets a single lens through at 0.75 and above, so a lens with a
    habit can carry a technique on its own indefinitely. Repetition is not
    corroboration, and the map must not read it as mastery."""
    graph: dict[str, SkillState] = {}
    for i in range(8):
        skills.apply_analysis(graph, analysis(f"s{i}", 9, ("panning", 0.95, 1)), T0)
    state = graph["panning"]
    assert state.attempts == 8 and state.corroborated == 0
    assert state.best_score == 9  # the frames were good; that is not the question
    assert state.status is SkillStatus.ATTEMPTED


def test_the_frame_score_is_recorded_but_promotes_nothing():
    """One photograph demonstrating three techniques hands the same score to
    all three. Status follows each technique's own evidence, so a corroborated
    one climbs and a single-lens one does not, off the identical frame."""
    graph: dict[str, SkillState] = {}
    for i in range(3):
        skills.apply_analysis(
            graph,
            analysis(
                f"s{i}",
                9,
                ("panning", 0.9, 2),
                ("golden_hour", 0.9, 1),
                ("leading_lines", 0.9, 2),
            ),
            T0 + timedelta(days=i),
        )
    assert {t: s.best_score for t, s in graph.items()} == {
        "panning": 9,
        "golden_hour": 9,
        "leading_lines": 9,
    }
    assert graph["panning"].status is SkillStatus.SOLID
    assert graph["leading_lines"].status is SkillStatus.SOLID
    assert graph["golden_hour"].status is SkillStatus.ATTEMPTED


def test_confident_but_alone_is_not_corroborated():
    assert not skills.corroborated(TechniqueEvidence(technique_id="x", confidence=1.0, agreement=1))
    assert not skills.corroborated(TechniqueEvidence(technique_id="x", confidence=0.7, agreement=3))
    assert skills.corroborated(TechniqueEvidence(technique_id="x", confidence=0.75, agreement=2))


def test_decay_and_recovery():
    graph: dict[str, SkillState] = {}
    for i in range(3):
        skills.apply_analysis(graph, analysis(f"s{i}", 8, ("panning", 0.9)), T0)
    assert graph["panning"].status is SkillStatus.SOLID
    assert skills.decay(graph, T0 + timedelta(days=10), decay_days=21) == []
    changed = skills.decay(graph, T0 + timedelta(days=30), decay_days=21)
    assert [s.technique_id for s in changed] == ["panning"]
    assert graph["panning"].status is SkillStatus.RUSTY
    skills.apply_analysis(graph, analysis("s9", 8, ("panning", 0.9)), T0 + timedelta(days=31))
    assert graph["panning"].status is SkillStatus.SOLID


def test_shot_memory_is_capped():
    graph: dict[str, SkillState] = {}
    for i in range(15):
        skills.apply_analysis(graph, analysis(f"s{i}", 7, ("panning", 0.9)), T0)
    assert len(graph["panning"].shot_ids) == skills.SHOT_MEMORY
    assert graph["panning"].attempts == 15


# --- scout ----------------------------------------------------------------


def test_empty_map_starts_at_level_one_and_skips_recent():
    first = scout.choose({}, recent_technique_ids=[])
    assert first is not None and first.level == 1 and not first.requires
    second = scout.choose({}, recent_technique_ids=[first.id])
    assert second is not None and second.id != first.id


def test_ranking_prefers_least_covered_family_then_catalogue_order():
    graph: dict[str, SkillState] = {}
    # Attempt several composition techniques; the next pick should leave composition.
    for tid in ["rule_of_thirds", "leading_lines", "fill_the_frame"]:
        skills.apply_analysis(graph, analysis(f"s_{tid}", 6, (tid, 0.9)), T0)
    pick = scout.choose(graph, [])
    assert pick is not None and pick.family.value != "composition"


def test_prerequisites_gate_and_unlock():
    graph: dict[str, SkillState] = {}
    ranked = {t.id for t in scout.rank(graph, [])}
    assert "rim_light" not in ranked  # requires backlight
    skills.apply_analysis(graph, analysis("s1", 6, ("backlight", 0.9)), T0)
    assert "rim_light" in {t.id for t in scout.rank(graph, [])}


def test_video_techniques_excluded_unless_asked():
    assert all(not t.video_only for t in scout.rank({}, []))
    assert any(t.video_only for t in scout.rank({}, [], video=True))


def test_rusty_is_offered_but_after_level_one_breadth():
    graph: dict[str, SkillState] = {}
    for i in range(3):
        skills.apply_analysis(graph, analysis(f"s{i}", 8, ("panning", 0.9)), T0)
    skills.decay(graph, T0 + timedelta(days=40), decay_days=21)
    ranked = scout.rank(graph, [])
    ids = [t.id for t in ranked]
    assert "panning" in ids and ranked[0].level == 1
    assert "rusty" in scout.why_now(
        ranked[ids.index("panning")], graph
    ).lower() or "solid" in scout.why_now(ranked[ids.index("panning")], graph)


def test_why_now_mentions_prerequisites():
    graph: dict[str, SkillState] = {}
    skills.apply_analysis(graph, analysis("s1", 6, ("backlight", 0.9)), T0)
    from app.domain import taxonomy

    text = scout.why_now(taxonomy.get("rim_light"), graph)
    assert "Backlight" in text
