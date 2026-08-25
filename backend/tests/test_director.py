"""Director on a real store and blob store; the generators return bytes made
here (Veo itself is checked by scripts/check_director.py against the model)."""

import tempfile

import pytest

from app.agents.director import Generators, Storyboard
from app.domain.entities import Criteria, ExifRule, Experiment, ExperimentStatus
from app.infra import repository as repo
from app.infra.bus import InProcessBus
from app.infra.drive import LocalDriveClient
from app.infra.secrets import LocalTokenStore
from app.infra.storage import LocalBlobStore
from app.infra.store import InMemoryStore
from app.services import director
from app.services.context import Context
from tests.fixtures import silent_clip

MESSAGE = {"user_id": "u1", "experiment_id": "quest_1"}


def experiment(status=ExperimentStatus.OPEN) -> Experiment:
    return Experiment(
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


def generators(calls: list[str]) -> Generators:
    async def board(technique, q):
        calls.append("storyboard")
        assert technique.id == q.technique_id
        return Storyboard(video_prompt="A cyclist panned against a blurred street.")

    async def clip(prompt):
        calls.append("clip")
        return silent_clip(2.0)

    return Generators(storyboard=board, clip=clip)


async def test_clip_lands_on_quest_and_is_idempotent():
    with tempfile.TemporaryDirectory() as folder:
        ctx = context(folder)
        await repo.put_experiment(ctx.store, experiment())
        calls: list[str] = []
        path = await director.direct(ctx, MESSAGE, generators(calls))
        assert path == "users/u1/experiments/quest_1/reference.mp4"
        assert await ctx.blobs.exists(path)
        stored = await repo.get_experiment(ctx.store, "quest_1")
        assert stored.reference_clip == path
        stages = [e.stage for e in await repo.list_events(ctx.store, "u1")]
        assert "storyboard" in stages and "clip_ready" in stages
        assert calls == ["storyboard", "clip"]

        again = await director.direct(ctx, MESSAGE, generators(calls))
        assert again == path and calls == ["storyboard", "clip"]


async def test_closed_quest_gets_no_clip():
    with tempfile.TemporaryDirectory() as folder:
        ctx = context(folder)
        await repo.put_experiment(ctx.store, experiment(ExperimentStatus.SKIPPED))
        calls: list[str] = []
        assert await director.direct(ctx, MESSAGE, generators(calls)) is None
        assert calls == []


async def test_unknown_quest_raises():
    with tempfile.TemporaryDirectory() as folder, pytest.raises(repo.UnknownEntity):
        await director.direct(context(folder), {**MESSAGE, "experiment_id": "nope"}, generators([]))
