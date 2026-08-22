"""Director on a real store, real blob store and real ffmpeg; the three
generators return bytes made here (Veo and Lyria themselves are checked by
scripts/check_director.py against the models)."""

import tempfile

import pytest

from app.agents.director import Generators, Storyboard, Track
from app.domain.entities import Criteria, ExifRule, Quest, QuestStatus
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.drive import LocalDriveClient
from app.infra.secrets import LocalTokenStore
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import director
from app.services.context import Context
from tests.test_mux import silent_clip, sine_wav

MESSAGE = {"user_id": "u1", "quest_id": "quest_1"}


def quest(status=QuestStatus.OPEN) -> Quest:
    return Quest(
        id="quest_1",
        user_id="u1",
        technique_id="panning",
        title="Follow the rider",
        brief="1. Stand by the road.\n2. Pan with the bike.",
        why_now="",
        criteria=Criteria(exif=ExifRule(), vision=["panning"], text=["motion-blurred background"]),
        status=status,
    )


def context(folder: str) -> Context:
    return Context(
        store=InMemoryStore(),
        blobs=LocalBlobStore(folder),
        bus=InProcessBus(),
        drive=LocalDriveClient(folder),
        tokens=LocalTokenStore(folder),
    )


def generators(calls: list[str], track_fails: bool = False) -> Generators:
    async def board(technique, q):
        calls.append("storyboard")
        assert technique.id == q.technique_id
        return Storyboard(
            video_prompt="A cyclist panned against a blurred street.", music_prompt="Soft lo-fi"
        )

    async def clip(prompt):
        calls.append("clip")
        return silent_clip(2.0)

    async def track(prompt):
        calls.append("track")
        if track_fails:
            raise RuntimeError("lyria down")
        return Track(data=sine_wav(5.0), mime_type="audio/wav")

    return Generators(storyboard=board, clip=clip, track=track)


async def test_clip_lands_on_quest_and_is_idempotent(monkeypatch):
    monkeypatch.setattr(director.settings, "clip_seconds", 2)
    with tempfile.TemporaryDirectory() as folder:
        ctx = context(folder)
        await repo.put_quest(ctx.store, quest())
        calls: list[str] = []
        path = await director.direct(ctx, MESSAGE, generators(calls))
        assert path == "users/u1/quests/quest_1/reference.mp4"
        assert await ctx.blobs.exists(path)
        stored = await repo.get_quest(ctx.store, "quest_1")
        assert stored.reference_clip == path
        kinds = [e.stage for e in await repo.list_events(ctx.store, "u1")]
        assert "storyboard" in kinds and "clip_ready" in kinds
        assert calls == ["storyboard", "clip", "track"]

        again = await director.direct(ctx, MESSAGE, generators(calls))
        assert again == path and calls == ["storyboard", "clip", "track"]


async def test_music_failure_ships_silent_clip(monkeypatch):
    monkeypatch.setattr(director.settings, "clip_seconds", 2)
    with tempfile.TemporaryDirectory() as folder:
        ctx = context(folder)
        await repo.put_quest(ctx.store, quest())
        path = await director.direct(ctx, MESSAGE, generators([], track_fails=True))
        assert path and await ctx.blobs.exists(path)
        events = await repo.list_events(ctx.store, "u1")
        ready = next(e for e in events if e.stage == "clip_ready")
        assert ready.detail["scored"] is False


async def test_closed_quest_gets_no_clip():
    with tempfile.TemporaryDirectory() as folder:
        ctx = context(folder)
        await repo.put_quest(ctx.store, quest(QuestStatus.SKIPPED))
        calls: list[str] = []
        assert await director.direct(ctx, MESSAGE, generators(calls)) is None
        assert calls == []


async def test_unknown_quest_raises():
    with tempfile.TemporaryDirectory() as folder, pytest.raises(repo.UnknownEntity):
        await director.direct(context(folder), {**MESSAGE, "quest_id": "nope"}, generators([]))
