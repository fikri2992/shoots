"""Cartographer rules and Scout ranking. Pure, exhaustive where cheap."""

from datetime import UTC, datetime, timedelta

from app.domain import scout, skills
from app.domain.entities import Analysis, SkillState, SkillStatus, TechniqueEvidence

T0 = datetime(2026, 8, 22, tzinfo=UTC)


def analysis(shot: str, score: int, *evidence: tuple[str, float]) -> Analysis:
    return Analysis(
        shot_id=shot,
        user_id="u",
        model="m",
        score=score,
        techniques=[TechniqueEvidence(technique_id=t, confidence=c) for t, c in evidence],
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


def test_a_bad_last_shot_keeps_solid_from_forming():
    graph: dict[str, SkillState] = {}
    for i, score in enumerate([8, 8, 3]):
        skills.apply_analysis(graph, analysis(f"s{i}", score, ("panning", 0.9)), T0)
    assert graph["panning"].status is SkillStatus.ATTEMPTED  # last 3 < practiced threshold


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
