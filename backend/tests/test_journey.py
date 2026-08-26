"""The Journey Update: written when the work moved, silent when it did not.

The writer is stubbed throughout. What is under test is everything that
decides *whether* to write and *what may be said* — all of which is arithmetic,
and none of which a model is allowed to touch.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities import (
    Analysis,
    Composition,
    Exif,
    GridSpec,
    Shot,
    ShotKind,
    TechniqueState,
    TechniqueStatus,
    Tone,
    User,
    now,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.store import InMemoryStore
from app.services import journey
from app.services.context import Context


@pytest.fixture(autouse=True)
def no_model(monkeypatch):
    """Every test here runs without a model. The paragraph is the last step and
    the least of it."""
    written = []

    async def fake_write(evidence, previous, taste_is_known):
        written.append({"evidence": evidence, "previous": previous, "taste": taste_is_known})
        return "You keep finding quiet corners."

    monkeypatch.setattr(journey.agent, "write", fake_write)
    return written


def ctx() -> Context:
    return Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)


async def seed(
    c: Context,
    n: int,
    *,
    subject=(0.5, 0.5),
    size=(800, 600),
    keepers: int = 0,
    minutes_apart: int = 30,
    start: int = 0,
) -> None:
    await repo.put_user(c.store, User(id="u1", email="u@x", drive_folder_id="local"))
    base = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
    for i in range(start, start + n):
        sid = f"s{i}"
        shot = Shot(
            id=sid,
            user_id="u1",
            kind=ShotKind.PHOTO,
            drive_file_id=sid,
            filename=f"{sid}.jpg",
            mime_type="image/jpeg",
            exif=Exif(captured_at=base + timedelta(minutes=i * minutes_apart)),
            tone=Tone(luma_mean=120, warm_share=30, cool_share=5),
            grid=GridSpec(cols=8, rows=6, width=size[0], height=size[1]),
            kept_at=(now() if (i - start) < keepers else None),
        )
        await repo.put_shot(c.store, shot)
        comp = Composition(subject_cells=["C1", "C2", "C3"])
        comp.subject_x, comp.subject_y = subject
        await repo.put_analysis(
            c.store, Analysis(shot_id=sid, user_id="u1", model="test", composition=comp)
        )


async def test_a_first_afternoon_gets_no_paragraph():
    """Who someone is as a photographer needs a body of work."""
    c = ctx()
    await seed(c, 4)
    assert await journey.maybe_write(c, "u1") is None


async def test_the_first_update_reports_the_whole_body_of_work():
    c = ctx()
    await seed(c, 12)
    update = await journey.maybe_write(c, "u1")
    assert update is not None
    assert update.shots == 12
    assert update.body == "You keep finding quiet corners."
    assert any("12 shots read in total" in line for line in update.evidence)


async def test_nothing_moved_writes_nothing():
    """The common case, and a real answer. An update that arrives with nothing
    behind it is the engagement-shaped noise this refuses to be."""
    c = ctx()
    await seed(c, 12)
    assert await journey.maybe_write(c, "u1") is not None
    await seed(c, 3, start=12)  # three more of exactly the same
    assert await journey.maybe_write(c, "u1") is None


async def test_a_dimension_that_widened_earns_the_next_update():
    c = ctx()
    await seed(c, 12)
    assert await journey.maybe_write(c, "u1") is not None
    await seed(c, 6, start=12, subject=(0.1, 0.5))  # a new placement bucket
    update = await journey.maybe_write(c, "u1")
    assert update is not None
    assert "placement" in update.widened
    assert any("first time shooting near the edge" in line for line in update.evidence)


async def test_the_second_update_diffs_against_the_first_not_against_nothing():
    """Without the stored counts the profile would re-report the whole corpus
    as new every time, and every paragraph would say the same thing."""
    c = ctx()
    await seed(c, 12)
    first = await journey.maybe_write(c, "u1")
    assert first is not None and first.counts["placement"] == {"centred": 12}
    await seed(c, 6, start=12, subject=(0.1, 0.5))
    second = await journey.maybe_write(c, "u1")
    assert second is not None and second.counts["placement"] == {"centred": 12, "near the edge": 6}


async def test_a_technique_becoming_recurring_earns_an_update_without_claiming_control():
    c = ctx()
    await seed(c, 12)
    await journey.maybe_write(c, "u1")
    await repo.put_technique_state(
        c.store,
        TechniqueState(
            user_id="u1",
            technique_id="backlight",
            status=TechniqueStatus.RECURRING,
            attempts=3,
            corroborated=3,
        ),
    )
    update = await journey.maybe_write(c, "u1")
    assert update is not None
    assert "backlight" in update.became_recurring
    recurrence = next(line for line in update.evidence if "now recurring" in line)
    assert "recurrence does not prove deliberate control" in recurrence
    assert all(word not in recurrence for word in ("reliably", "repeatable", "corroborat"))


async def test_retracted_recurrence_writes_a_code_authored_correction(no_model):
    c = ctx()
    await seed(c, 12)
    await repo.put_technique_state(
        c.store,
        TechniqueState(
            user_id="u1",
            technique_id="backlight",
            status=TechniqueStatus.RECURRING,
            attempts=3,
            corroborated=3,
        ),
    )
    first = await journey.maybe_write(c, "u1")
    assert first is not None and first.became_recurring == ["backlight"]
    writer_calls = len(no_model)

    await repo.put_technique_state(
        c.store,
        TechniqueState(
            user_id="u1",
            technique_id="backlight",
            status=TechniqueStatus.OBSERVED,
            attempts=3,
            corroborated=0,
        ),
    )
    correction = await journey.maybe_write(c, "u1")

    assert correction is not None
    assert "corrected an earlier record" in correction.body
    assert "repeatable" not in correction.body
    assert any("system correction" in line and "backlight" in line for line in correction.evidence)
    assert correction.provenance.model == "" and correction.provenance.prompt_version == ""
    assert len(no_model) == writer_calls


async def test_without_keepers_the_writer_is_told_not_to_speak_about_taste():
    c = ctx()
    await seed(c, 12)
    update = await journey.maybe_write(c, "u1")
    assert update is not None and update.taste_is_known is False
    assert any("do not speak about taste" in line for line in update.evidence)
    assert not any("keep" in line and "times as often" in line for line in update.evidence)


async def test_keeper_distribution_reaches_the_writer_as_positive_marks():
    c = ctx()
    await seed(c, 12, keepers=6)
    update = await journey.maybe_write(c, "u1")
    assert update is not None and update.taste_is_known is True
    marked = "marked as Keepers by the photographer themselves"
    assert any(marked in line for line in update.evidence)
    assert any("6 of 6 readable marked Keepers" in line for line in update.evidence)


async def test_the_evidence_never_carries_a_score(no_model):
    """Decision 39: the update may say the photographer changed and may never
    say the photographs got better. The panel's number is not in the room."""
    c = ctx()
    await seed(c, 12)
    update = await journey.maybe_write(c, "u1")
    assert update is not None
    joined = " ".join(update.evidence).lower()
    for forbidden in ("score", "out of 10", "rating", "grade", "better", "improved"):
        assert forbidden not in joined


async def test_blind_spots_reach_the_writer():
    c = ctx()
    await seed(c, 12)
    update = await journey.maybe_write(c, "u1")
    assert update is not None
    assert any("cannot see" in line and "height" in line for line in update.evidence)


async def test_the_paragraph_failing_does_not_lose_the_figures(monkeypatch):
    """A model outage costs the sentences, not the update."""

    async def broken(*args, **kwargs):
        return ""

    monkeypatch.setattr(journey.agent, "write", broken)
    c = ctx()
    await seed(c, 12)
    update = await journey.maybe_write(c, "u1")
    assert update is not None and update.body == "" and update.evidence


async def test_the_first_update_does_not_call_the_whole_corpus_new():
    """Everything diffs against an empty profile the first time. Handing that
    to the writer as change would make the opening paragraph a lie."""
    c = ctx()
    await seed(c, 12)
    update = await journey.maybe_write(c, "u1")
    assert update is not None
    assert not any("first time shooting" in line for line in update.evidence)
    assert not any("since the last update" in line for line in update.evidence)


async def test_the_evidence_never_names_the_machinery():
    """The writer repeats whatever words it is given. A photographer should
    never read the word 'lens' about their own photograph."""
    c = ctx()
    await seed(c, 12)
    await journey.maybe_write(c, "u1")
    await repo.put_technique_state(
        c.store,
        TechniqueState(
            user_id="u1",
            technique_id="low_angle",
            status=TechniqueStatus.RECURRING,
            attempts=3,
            corroborated=3,
        ),
    )
    update = await journey.maybe_write(c, "u1")
    assert update is not None
    joined = " ".join(update.evidence).lower()
    for machinery in ("lens", "confidence", "corroborat", "panel", "agreement"):
        assert machinery not in joined


# --- provenance -----------------------------------------------------------------


async def test_a_claim_names_its_own_sample_and_arithmetic():
    """A claim about a body of work is not checkable the way one Finding is:
    the reader cannot open a file and see the figure. What makes it honest is
    knowing exactly which Shots produced it, and under which calculation."""
    from app.domain import tendency

    c = ctx()
    await seed(c, 12)
    update = await journey.maybe_write(c, "u1")
    assert update is not None

    prov = update.provenance
    assert prov.sample_size == 12
    assert len(prov.shot_ids) == 12
    assert set(prov.shot_ids) == {f"s{i}" for i in range(12)}
    assert prov.calc_version == tendency.CALC_VERSION


async def test_the_prompt_that_wrote_the_words_is_recorded_with_them():
    from app.agents import prompts

    c = ctx()
    await seed(c, 12)
    update = await journey.maybe_write(c, "u1")
    assert update is not None
    assert update.provenance.prompt_version == prompts.version("journey")
    assert update.provenance.model


async def test_an_update_with_no_paragraph_claims_no_model_wrote_one(monkeypatch):
    """The figures stand on their own when the writer fails. Recording a model
    against sentences that do not exist would be a false attribution."""

    async def broken(*args, **kwargs):
        return ""

    monkeypatch.setattr(journey.agent, "write", broken)
    c = ctx()
    await seed(c, 12)
    update = await journey.maybe_write(c, "u1")
    assert update is not None and update.body == ""
    assert update.provenance.model == "" and update.provenance.prompt_version == ""
    assert update.provenance.sample_size == 12  # the measured half is untouched


def test_editing_a_prompt_changes_its_recorded_version():
    """The wording is part of what makes a claim reproducible: a paragraph
    written under different instructions is a different paragraph."""
    from app.agents import prompts

    assert prompts.version("journey") != prompts.version("judge")
    assert len(prompts.version("journey")) == 12
