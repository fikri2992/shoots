"""What may cross the boundary to a photographer, and in what words.

Every other test here checks a rule at the layer that decides it. These check
the layer that *publishes* it, because that is where both of the product's
standing promises were quietly broken while the suite stayed green:

* the score reached the browser on every shot, because ``ShotView`` embedded
  the whole ``Analysis`` entity and an entity publishes every field it has;
* forbidden vocabulary reached two live model prompts and a UI legend, because
  a rename swept the identifiers and left the sentences.

Neither is visible from a unit test of the thing that was right. So these read
the actual HTTP responses and the actual strings, and they are deliberately
blunt: a leak should fail here even when it is invisible on screen, because
invisible is exactly how both of them survived.
"""

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import deps, main
from app.api.auth import current_user
from app.domain.entities import (
    Analysis,
    Composition,
    GridSpec,
    Shot,
    ShotKind,
    ShotStatus,
    TechniqueEvidence,
    User,
    now,
)
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.store import InMemoryStore
from app.services.context import Context

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client():
    """The real app, with a signed-in user and an in-memory store."""
    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    main.app.dependency_overrides[deps.get_context] = lambda: ctx
    main.app.dependency_overrides[current_user] = lambda: {"id": "u1", "email": "u@x"}
    with TestClient(main.app) as test_client:
        test_client.ctx = ctx
        yield test_client
    main.app.dependency_overrides.clear()


async def seed(ctx: Context) -> None:
    await repo.put_user(ctx.store, User(id="u1", email="u@x", drive_folder_id="local"))
    shot = Shot(
        id="shot_1",
        user_id="u1",
        kind=ShotKind.PHOTO,
        drive_file_id="d1",
        filename="a.jpg",
        mime_type="image/jpeg",
        status=ShotStatus.ANALYZED,
        grid=GridSpec(cols=8, rows=6, width=1600, height=1200),
        analyzed_at=now(),
    )
    await repo.put_shot(ctx.store, shot)
    await repo.put_analysis(
        ctx.store,
        Analysis(
            shot_id="shot_1",
            user_id="u1",
            model="gemini-3.7-flash",
            techniques=[TechniqueEvidence(technique_id="backlight", confidence=0.8, agreement=2)],
            composition=Composition(subject_cells=["C3"], guide="thirds"),
            observations=["the light is behind them"],
            critique="works",
            elements={"impact": 8, "composition": 6},
            score=9,
        ),
    )


# --- the score reaches nothing a photographer can read ---------------------


#: Every read endpoint a signed-in photographer's client actually calls.
READ_ENDPOINTS = (
    "/api/shots?limit=10",
    "/api/shots/shot_1",
    "/api/events?limit=50",
    "/api/profile",
    "/api/journey?limit=5",
    "/api/techniques",
    "/api/experiments?limit=5",
)


@pytest.mark.parametrize("path", READ_ENDPOINTS)
async def test_no_user_facing_endpoint_returns_a_score(client, path):
    """Decision 46: the score is stored and read by nothing. "Nothing" has to
    include the wire, or the first component that renders `analysis.score`
    restores the report card with no server change and no failing test."""
    await seed(client.ctx)
    response = client.get(path)
    assert response.status_code == 200, response.text

    body = response.json()
    for field in ("score", "elements", "best_score", "last_score"):
        assert field not in json.dumps(body), f"{path} published {field}"


async def test_the_analysis_a_photographer_receives_still_carries_its_evidence(client):
    """The point is to drop the score, not to hollow out the read. What makes a
    Finding checkable has to survive."""
    await seed(client.ctx)
    view = client.get("/api/shots/shot_1").json()["analysis"]
    assert view["techniques"][0]["technique_id"] == "backlight"
    assert view["observations"] == ["the light is behind them"]
    assert view["composition"]["guide"] == "thirds"
    assert view["critique"] == "works"


# --- the vocabulary lock -----------------------------------------------------


#: Words the product retired, and what replaced them. `solid`, `rusty` and the
#: rest graded a person; `quest` and `fault` were the old nouns. A word here
#: must not appear in anything a photographer reads or a model is told.
RETIRED = {
    "quest": "experiment",
    "rusty": "recurring",
    "unexplored": "unobserved",
    "practised": "observed",
    "practiced": "observed",
    "skill graph": "technique map",
    "level up": "nothing - the map does not level anyone",
}

#: Where a retired word would actually reach someone: the prompts a model is
#: given, and the templates a photographer reads.
SURFACES = (
    *(ROOT / "backend/app/agents/prompts").glob("*.md"),
    *(ROOT / "frontend/src/components").rglob("*.vue"),
    *(ROOT / "frontend/src/pages").glob("*.vue"),
)


@pytest.mark.parametrize("path", SURFACES, ids=lambda p: p.name)
def test_no_retired_word_reaches_a_prompt_or_a_screen(path: Path):
    """The rename swept identifiers and left the sentences, so `solid` survived
    inside a live tool description and `practised` inside a legend. Identifiers
    are checked by the compiler; prose is checked here or nowhere.

    Whole words only - `quest` lives inside `question`, and a blunter check
    would be turned off within the week for crying wolf.
    """
    text = path.read_text(encoding="utf-8").lower()
    for retired, instead in RETIRED.items():
        pattern = rf"\b{re.escape(retired)}\b"
        assert not re.search(pattern, text), (
            f"{path.name} still says {retired!r}; use {instead!r}"
        )


def test_the_words_that_replaced_them_are_actually_in_use():
    """The negative test above passes trivially on an empty file. This one
    fails if the vocabulary was deleted rather than replaced."""
    joined = " ".join(p.read_text(encoding="utf-8").lower() for p in SURFACES)
    for word in ("experiment", "recurring", "unobserved", "technique"):
        assert word in joined


def test_no_retired_word_reaches_the_coach_as_a_tool_description():
    """The Coach's tools are declared in Python, not in a prompt file, which is
    how "the photographer's skill graph: what they have attempted, what is
    solid" survived the rename inside a live model instruction. The words a
    model is handed are a surface like any other."""
    from app.agents import coach as coach_agent

    declared = " ".join(
        f"{fn.name} {fn.description or ''}"
        for fn in (coach_agent.TOOLS.function_declarations or [])
    ).lower()
    assert declared
    for retired, instead in {**RETIRED, "solid": "recurring"}.items():
        assert not re.search(rf"\b{re.escape(retired)}\b", declared), (
            f"a Coach tool still says {retired!r}; use {instead!r}"
        )


async def test_the_coachs_technique_map_tool_hands_over_evidence_not_a_score():
    """The Coach speaks out loud, so anything in a tool result is something the
    photographer hears. It used to read `best_score`, which is one frame's
    number shared by every Technique that frame demonstrated."""
    from app.domain.entities import TechniqueState, TechniqueStatus
    from app.services import coach as coach_service

    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    await repo.put_user(ctx.store, User(id="u1", email="u@x"))
    await repo.put_skill(
        ctx.store,
        TechniqueState(
            user_id="u1",
            technique_id="backlight",
            status=TechniqueStatus.RECURRING,
            attempts=5,
            corroborated=3,
            best_score=9,
            last_score=7,
        ),
    )

    result = await coach_service.run_tool(ctx, "u1", "technique_map", {})

    assert result["ok"] is True
    spoken = json.dumps(result)
    assert "9" not in spoken and "/10" not in spoken
    assert "seen 5, confirmed 3" in spoken
    assert "recurring" in result["by_status"]
    summary = coach_service.summarise_tool("technique_map", result)
    assert summary.startswith("read the technique map")


async def test_an_unknown_coach_tool_is_refused_rather_than_guessed():
    from app.services import coach as coach_service

    ctx = Context(store=InMemoryStore(), blobs=None, bus=InProcessBus(), drive=None, tokens=None)
    result = await coach_service.run_tool(ctx, "u1", "skill_map", {})
    assert result["ok"] is False and "unknown tool" in result["error"]
