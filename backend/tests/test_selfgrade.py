"""The coach checking its own advice (decision 37).

An agent that never checks its own recommendations is a critique queue. What
is measured is whether comparable behaviour differs — never whether the
photographs got better, which stays the panel's opinion and is labelled as one,
and never that the Experiment is *why*, which two frozen counts cannot know.

Three answers, not two. `insufficient evidence` is the one that makes the other
two worth anything: without it a photographer who did not go out reads as
advice that failed, and good advice is retired on no evidence at all.
"""

import pytest

from app.domain import tendency
from app.domain.entities import ChangeState, Comparability

PLACEMENT = tendency.PLACEMENT


def test_shooting_something_never_shot_before_is_unambiguous():
    changed = tendency.change(
        PLACEMENT,
        at_issue={"centred": 12},
        now_counts={"centred": 13, "near the edge": 5},
        shots_since=6,
    )
    assert changed.state is ChangeState.CHANGED
    assert changed.new_buckets == ["near the edge"]
    assert "first near the edge in 6 shots since" in changed.outcome


def test_a_distribution_that_merely_evened_out_counts_when_it_moved_enough():
    changed = tendency.change(
        PLACEMENT,
        at_issue={"centred": 12, "off centre": 1},
        now_counts={"centred": 12, "off centre": 8},
        shots_since=7,
    )
    assert changed.state is ChangeState.CHANGED and "spread wider" in changed.outcome


def test_more_of_the_same_is_unchanged():
    """The honest answer, and the one that retires advice that does not work."""
    changed = tendency.change(
        PLACEMENT, at_issue={"centred": 12}, now_counts={"centred": 20}, shots_since=8
    )
    assert changed.state is ChangeState.UNCHANGED
    assert changed.comparability is Comparability.COMPARABLE
    assert "8 shots since, same distribution" in changed.outcome


def test_a_narrowing_dimension_is_not_a_change():
    changed = tendency.change(
        PLACEMENT,
        at_issue={"centred": 6, "off centre": 6},
        now_counts={"centred": 16, "off centre": 6},
        shots_since=10,
    )
    assert changed.state is ChangeState.UNCHANGED


# --- the third answer ------------------------------------------------------


def test_nothing_shot_since_is_told_apart_from_advice_that_failed():
    """A photographer who did not go out has not ignored the advice. Counting
    that as `unchanged` would retire good advice on no evidence."""
    changed = tendency.change(
        PLACEMENT, at_issue={"centred": 12}, now_counts={"centred": 12}, shots_since=0
    )
    assert changed.state is ChangeState.INSUFFICIENT
    assert changed.comparability is Comparability.TOO_FEW_SHOTS
    assert changed.outcome == "nothing shot since"
    assert changed.added == 0


def test_one_frame_cannot_carry_a_change():
    """A single frame can put a bucket on the board. Calling that movement
    credits the advice for arithmetic, so below the floor the answer is that
    there is nothing to compare yet — and it stays open to be asked again."""
    changed = tendency.change(
        PLACEMENT,
        at_issue={"centred": 12},
        now_counts={"centred": 12, "near the edge": 1},
        shots_since=1,
    )
    assert changed.state is ChangeState.INSUFFICIENT
    assert changed.settled is False
    assert "1 shot since" in changed.outcome


def test_shots_that_the_dimension_cannot_read_are_reported_as_shots():
    """Height needs the Shoots camera's pitch and light needs GPS, so a whole
    import can leave a dimension's counts untouched. The frames still happened:
    telling someone who shot forty that they shot none is the exact failure the
    module exists to avoid."""
    changed = tendency.change(
        tendency.HEIGHT,
        at_issue={"eye level": 8},
        now_counts={"eye level": 8},
        shots_since=40,
    )
    assert changed.state is ChangeState.INSUFFICIENT
    assert "40 shots since" in changed.outcome
    assert "none of them showing the height you shoot from" in changed.outcome


def test_a_corpus_that_shrank_says_so_rather_than_reporting_negative_shooting():
    """Past the read window older frames drop out and the subtraction goes
    negative. "-5 shots since" is not a sentence anyone should read."""
    changed = tendency.change(
        PLACEMENT, at_issue={"centred": 100}, now_counts={"centred": 20}, shots_since=-80
    )
    assert changed.state is ChangeState.INSUFFICIENT
    assert "no longer all there" in changed.outcome


def test_only_a_sample_that_can_still_grow_is_left_open():
    """Being asked again is the difference between "not yet" and "never". A
    baseline frozen by other arithmetic will not become comparable, so it is
    written once; a small sample is re-checked as the photographer shoots."""
    too_few = tendency.change(
        PLACEMENT, at_issue={"centred": 12}, now_counts={"centred": 13}, shots_since=1
    )
    from app.domain.entities import Change

    stale = Change(
        state=ChangeState.INSUFFICIENT, comparability=Comparability.DIFFERENT_ARITHMETIC
    )
    settled = tendency.change(
        PLACEMENT, at_issue={"centred": 12}, now_counts={"centred": 20}, shots_since=8
    )
    assert too_few.settled is False
    assert stale.settled is True and settled.settled is True


# --- dwell -----------------------------------------------------------------


def test_working_the_scene_needs_more_than_one_scene_to_be_a_ratio():
    """Eight frames of one afternoon is an afternoon, not a tendency."""
    changed = tendency.dwell_change(
        {"shots": 18, "scenes": 16}, tendency.Dwell(scenes=17, shots=26, longest=8)
    )
    assert changed.state is ChangeState.INSUFFICIENT
    assert "across 1 scene" in changed.outcome


def test_staying_with_a_scene_shows_up_as_a_change():
    changed = tendency.dwell_change(
        {"shots": 18, "scenes": 16}, tendency.Dwell(scenes=20, shots=30, longest=5)
    )
    assert changed.state is ChangeState.CHANGED
    assert "up from 1.1" in changed.outcome


def test_walking_on_at_the_same_rate_is_unchanged():
    changed = tendency.dwell_change(
        {"shots": 18, "scenes": 16}, tendency.Dwell(scenes=24, shots=27, longest=2)
    )
    assert changed.state is ChangeState.UNCHANGED


# --- what it must never say ------------------------------------------------


#: Words that would turn two facts into a claim about cause. The Change reports
#: what the counts did; whether the Experiment is why is not available from a
#: frozen count, and asserting it is the flattery this product exists to avoid.
CAUSAL = ("because", "caused", "thanks to", "so you", "worked", "improved", "better", "result of")


def every_outcome() -> list[str]:
    """One sentence from every branch either function can reach."""
    counts = [
        ({"centred": 12}, {"centred": 13, "near the edge": 5}, 6),
        ({"centred": 12, "off centre": 1}, {"centred": 12, "off centre": 8}, 7),
        ({"centred": 12}, {"centred": 20}, 8),
        ({"centred": 12}, {"centred": 12}, 0),
        ({"centred": 12}, {"centred": 13}, 1),
        ({"centred": 12}, {"centred": 12}, 40),
        ({"centred": 100}, {"centred": 20}, -80),
    ]
    out = [tendency.change(PLACEMENT, a, b, shots_since=n).outcome for a, b, n in counts]
    dwells = [
        tendency.Dwell(scenes=17, shots=26, longest=8),
        tendency.Dwell(scenes=20, shots=30, longest=5),
        tendency.Dwell(scenes=24, shots=27, longest=2),
        tendency.Dwell(scenes=16, shots=18, longest=2),
    ]
    return out + [tendency.dwell_change({"shots": 18, "scenes": 16}, d).outcome for d in dwells]


@pytest.mark.parametrize("outcome", every_outcome())
def test_no_outcome_claims_the_experiment_caused_anything(outcome: str):
    lowered = outcome.lower()
    assert not any(word in lowered for word in CAUSAL), outcome
    assert outcome and outcome[0].islower() or outcome[0].isdigit()


def test_a_change_is_reproducible_from_counts_alone():
    """Both halves are plain integers, so a Change can be recomputed from the
    store years later without a model, a photograph, or a prompt — which means
    the pure arithmetic must not stamp a time on it."""
    args = (tendency.FRAMING, {"wide": 9}, {"wide": 9, "close": 4}, 4)
    first, second = tendency.change(*args), tendency.change(*args)
    assert first == second
    assert first.checked_at is None


# --- the service: what may be compared at all ------------------------------


async def context():
    from app.domain.entities import User
    from app.infra import repository as repo
    from app.infra.bus import InProcessBus
    from app.infra.store import InMemoryStore
    from app.services.context import Context

    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    await repo.put_user(ctx.store, User(id="u1", email="u@x", drive_folder_id="local"))
    return ctx


def experiment(eid: str, *, version: str, sample: int = 18):
    from app.domain.entities import (
        Baseline,
        Criteria,
        Experiment,
        ExperimentStatus,
        Provenance,
    )

    return Experiment(
        id=eid,
        user_id="u1",
        technique_id="low_angle",
        title="t",
        brief="b",
        why_now="w",
        criteria=Criteria(),
        status=ExperimentStatus.COMPLETED,
        baseline=Baseline(
            source="placement",
            citation="10 of 10 readable shots: centred",
            at_issue={"centred": 10},
            calc_version=version,
            provenance=Provenance(sample_size=sample, calc_version=version),
        ),
    )


async def test_a_baseline_frozen_by_older_arithmetic_is_not_compared_across():
    """A Change is only meaningful against the calculation that produced its
    baseline. Diffing across a version bump would report a difference the
    photographer never made, so it is recorded as incomparable and said so —
    not skipped, which would read as though nobody looked."""
    from app.infra import repository as repo
    from app.services import scout

    ctx = await context()
    await repo.put_experiment(ctx.store, experiment("stale", version="tendency-0"))
    await repo.put_experiment(ctx.store, experiment("current", version=tendency.CALC_VERSION))
    await scout.grade_advice(ctx, "u1")

    stale = (await repo.get_experiment(ctx.store, "stale")).change
    current = (await repo.get_experiment(ctx.store, "current")).change
    assert stale.state is ChangeState.INSUFFICIENT
    assert stale.comparability is Comparability.DIFFERENT_ARITHMETIC
    assert "do not compare" in stale.outcome
    assert current.comparability is not Comparability.DIFFERENT_ARITHMETIC


async def test_a_baseline_with_no_recorded_sample_cannot_say_how_much_was_shot_since():
    """Experiments issued before the baseline kept its provenance. Their counts
    are still on disk, but nothing says how many frames they were taken over,
    so "shots since" has no honest value and the Change says that instead."""
    from app.infra import repository as repo
    from app.services import scout

    ctx = await context()
    await repo.put_experiment(
        ctx.store, experiment("old", version=tendency.CALC_VERSION, sample=0)
    )
    await scout.grade_advice(ctx, "u1")

    change = (await repo.get_experiment(ctx.store, "old")).change
    assert change.comparability is Comparability.UNRECORDED_SAMPLE
    assert change.settled is True


async def test_a_too_small_sample_is_asked_again_and_a_settled_one_is_not():
    """The re-check rule, which is the whole reason `settled` exists: a sample
    that can still grow must be revisited, or a photographer who shoots next
    week is stuck with 'nothing shot since' forever."""
    from app.domain.entities import ChangeState as State
    from app.infra import repository as repo
    from app.services import scout

    ctx = await context()
    await repo.put_experiment(ctx.store, experiment("open", version=tendency.CALC_VERSION))
    await repo.put_experiment(
        ctx.store, experiment("settled", version="tendency-0")
    )

    assert {e.id for e in await scout.grade_advice(ctx, "u1")} == {"open", "settled"}
    assert (await repo.get_experiment(ctx.store, "open")).change.state is State.INSUFFICIENT

    # Second pass: only the one that could still change its answer is re-asked.
    assert {e.id for e in await scout.grade_advice(ctx, "u1")} == {"open"}


async def test_a_baseline_is_frozen_only_when_the_tendency_chose_the_technique(monkeypatch):
    """The Scout freezes a tendency only when that tendency actually picked the
    technique. The ranking can land elsewhere - prerequisites, missing gear, a
    technique used too recently - and grading that advice against a tendency it
    was never aimed at would be the coach marking its own homework with someone
    else's answers.
    """
    import tempfile

    from app.domain import taxonomy
    from app.infra import repository as repo
    from app.services import scout
    from tests.test_first_experiment import context, stub_model

    stub_model(monkeypatch, [])
    with tempfile.TemporaryDirectory() as folder:
        ctx = context(folder)
        from app.domain.entities import User

        await repo.put_user(ctx.store, User(id="u1", email="a@b.c"))

        aimed = rules_challenge(monkeypatch, scout, prefers=("rule_of_thirds",))
        chosen = await scout.issue(ctx, "u1", technique_id="rule_of_thirds")
        assert chosen.baseline is not None
        assert chosen.baseline.citation == aimed.citation
        # The citation reaches the card as data, not only as the model's prose.
        assert chosen.baseline.at_issue == {}  # nothing shot yet; still frozen

        # Same tendency, a technique it does not prefer: no baseline at all, so
        # there is nothing for the coach to grade itself against later.
        elsewhere = next(t.id for t in taxonomy.TECHNIQUES if t.id not in aimed.prefers)
        other = await scout.issue(ctx, "u1", force=True, technique_id=elsewhere)
        assert other.baseline is None

        checked = await scout.grade_advice(ctx, "u1")
        assert [e.id for e in checked] == [chosen.id]


def rules_challenge(monkeypatch, scout_module, prefers: tuple[str, ...]):
    """Pin the profile's suggestion so the test is about the aiming rule."""
    challenge = tendency.Challenge(
        citation="12 of 18 readable shots: centred", prefers=prefers, source="placement"
    )
    monkeypatch.setattr(scout_module.tendency, "challenge_for", lambda profile: challenge)
    return challenge
