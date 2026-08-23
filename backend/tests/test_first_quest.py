"""The first quest arrives without being asked.

The model calls are replaced with the values a run would return; everything
else — store, bus, timing, the "one open quest" rule — is the real thing.
"""

import tempfile

from app.agents.scout import QuestOut, Research
from app.domain.entities import Criteria, ExifRule, Quest, QuestStatus, User
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.drive import LocalDriveClient
from app.infra.secrets import LocalTokenStore
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import scout
from app.services.context import Context


def context(folder: str) -> Context:
    return Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(folder),
        bus=InProcessBus(),
        drive=LocalDriveClient(folder),
        tokens=LocalTokenStore(folder),
    )


def stub_model(monkeypatch, calls: list[str]) -> None:
    async def research(technique):
        calls.append("research")
        return Research(notes=f"Notes on {technique.name}.", references=[])

    async def write(technique, why, critiques, notes, skills, constraints):
        calls.append("write")
        return QuestOut(
            title=f"Try {technique.name}",
            brief="1. Go outside.\n2. Take the photo.",
            why_now=why,
            criteria_text=["the technique is visible in the frame"],
        )

    monkeypatch.setattr(scout.agent, "research", research)
    monkeypatch.setattr(scout.agent, "write", write)


async def test_first_frames_earn_a_quest_with_no_one_asking(monkeypatch):
    calls: list[str] = []
    stub_model(monkeypatch, calls)
    with tempfile.TemporaryDirectory() as folder:
        ctx = context(folder)
        await repo.put_user(ctx.store, User(id="u1", email="a@b.c", name="A"))

        quest = await scout.issue_first(ctx, "u1")

        assert quest is not None and quest.status is QuestStatus.OPEN
        assert calls == ["research", "write"]
        assert await repo.open_quest(ctx.store, "u1") is not None


async def test_it_only_ever_fires_once(monkeypatch):
    calls: list[str] = []
    stub_model(monkeypatch, calls)
    with tempfile.TemporaryDirectory() as folder:
        ctx = context(folder)
        await repo.put_user(ctx.store, User(id="u1", email="a@b.c", name="A"))
        # A quest that is already finished still counts as a history.
        await repo.put_quest(
            ctx.store,
            Quest(
                id="quest_old",
                user_id="u1",
                technique_id="panning",
                title="Follow the rider",
                brief="1. Stand by the road.",
                why_now="",
                criteria=Criteria(exif=ExifRule(), vision=["panning"], text=[]),
                status=QuestStatus.PASSED,
            ),
        )

        assert await scout.issue_first(ctx, "u1") is None
        assert calls == []
