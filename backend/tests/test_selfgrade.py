"""The coach grading its own advice (decision 37).

An agent that never checks its own recommendations is a critique queue. What
is measured is whether behaviour moved — never whether the photographs got
better, which stays the panel's opinion and is labelled as one.
"""

from app.domain import tendency


def test_shooting_something_never_shot_before_is_unambiguous_movement():
    graded = tendency.grade(
        tendency.PLACEMENT,
        at_issue={"centred": 12},
        now_counts={"centred": 13, "near the edge": 5},
    )
    assert graded.moved is True
    assert graded.new_buckets == ("near the edge",)
    assert "first near the edge in 6 shots since" in graded.outcome


def test_a_distribution_that_merely_evened_out_counts_when_it_moved_enough():
    graded = tendency.grade(
        tendency.PLACEMENT,
        at_issue={"centred": 12, "off centre": 1},
        now_counts={"centred": 12, "off centre": 8},
    )
    assert graded.moved is True and "spread wider" in graded.outcome


def test_more_of_the_same_is_not_movement():
    """The honest answer, and the one that retires advice that does not work."""
    graded = tendency.grade(
        tendency.PLACEMENT, at_issue={"centred": 12}, now_counts={"centred": 20}
    )
    assert graded.moved is False
    assert "8 shots since, same distribution" in graded.outcome


def test_nothing_shot_since_is_told_apart_from_advice_that_failed():
    """A photographer who did not go out has not ignored the advice. Counting
    that as a failure would retire good advice on no evidence."""
    graded = tendency.grade(
        tendency.PLACEMENT, at_issue={"centred": 12}, now_counts={"centred": 12}
    )
    assert graded.moved is False and graded.outcome == "nothing shot since"
    assert graded.added == 0


def test_a_narrowing_dimension_is_not_movement():
    graded = tendency.grade(
        tendency.PLACEMENT,
        at_issue={"centred": 6, "off centre": 6},
        now_counts={"centred": 16, "off centre": 6},
    )
    assert graded.moved is False


def test_grading_is_reproducible_from_counts_alone():
    """Both halves are plain integers, so a grade can be recomputed from the
    store years later without a model, a photograph, or a prompt."""
    args = (tendency.FRAMING, {"wide": 9}, {"wide": 9, "close": 4})
    assert tendency.grade(*args) == tendency.grade(*args)
