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
    """Height needs recorded pitch and light needs GPS, so a whole
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

    stale = Change(state=ChangeState.INSUFFICIENT, comparability=Comparability.DIFFERENT_ARITHMETIC)
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
    from app.domain.entities import Analysis, Composition, GridSpec, Shot, ShotKind, User
    from app.infra import repository as repo
    from app.infra.bus import InProcessBus
    from app.infra.store import InMemoryStore
    from app.services.context import Context

    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    await repo.put_user(ctx.store, User(id="u1", email="u@x", drive_folder_id="local"))
    for index in range(18):
        shot_id = f"baseline_{index}"
        await repo.put_shot(
            ctx.store,
            Shot(
                id=shot_id,
                user_id="u1",
                kind=ShotKind.PHOTO,
                drive_file_id=shot_id,
                filename=f"{shot_id}.jpg",
                mime_type="image/jpeg",
                grid=GridSpec(cols=8, rows=6, width=800, height=600),
            ),
        )
        await repo.put_analysis(
            ctx.store,
            Analysis(
                shot_id=shot_id,
                user_id="u1",
                model="reader",
                composition=Composition(subject_x=0.5, subject_y=0.5, subject_cells=["D3"]),
            ),
        )
    return ctx


def experiment(eid: str, *, version: str, sample: int = 18):
    from app.domain.entities import (
        Analysis,
        Baseline,
        Composition,
        Criteria,
        Experiment,
        ExperimentStatus,
        ModelProvenance,
        Provenance,
    )

    read_version = tendency.model_read_version(
        Analysis(
            shot_id="baseline",
            user_id="u1",
            model="reader",
            composition=Composition(subject_x=0.5, subject_y=0.5, subject_cells=["D3"]),
        )
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
            citation=f"{sample} of {sample} readable Shots: centred",
            at_issue={"centred": sample} if sample else {"centred": 10},
            calc_version=version,
            provenance=Provenance(
                shot_ids=[f"baseline_{index}" for index in range(sample)],
                sample_size=sample,
                calc_version=version,
                inputs=[ModelProvenance(model="reader", prompt_version="")] if sample else [],
                analysis_versions={f"baseline_{index}": read_version for index in range(sample)},
            ),
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
    await scout.check_advice(ctx, "u1")

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
    await repo.put_experiment(ctx.store, experiment("old", version=tendency.CALC_VERSION, sample=0))
    await scout.check_advice(ctx, "u1")

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
    await repo.put_experiment(ctx.store, experiment("settled", version="tendency-0"))

    assert {e.id for e in await scout.check_advice(ctx, "u1")} == {"open", "settled"}
    assert (await repo.get_experiment(ctx.store, "open")).change.state is State.INSUFFICIENT

    # Second pass: only the one that could still change its answer is re-asked.
    assert {e.id for e in await scout.check_advice(ctx, "u1")} == {"open"}


async def test_reanalysis_under_the_same_prompt_forces_a_new_model_read_baseline():
    from app.infra import repository as repo
    from app.services import scout

    ctx = await context()
    await repo.put_experiment(ctx.store, experiment("model_read", version=tendency.CALC_VERSION))
    analysis = await repo.find_analysis(ctx.store, "baseline_0")
    assert analysis is not None
    analysis.composition.subject_x = 0.1
    await repo.put_analysis(ctx.store, analysis)

    await scout.check_advice(ctx, "u1")

    change = (await repo.get_experiment(ctx.store, "model_read")).change
    assert change.comparability is Comparability.DIFFERENT_MODEL_READING
