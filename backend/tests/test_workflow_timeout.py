"""The workflow budget must return control even if ADK cleanup resists cancellation."""

import asyncio
import time
from collections.abc import AsyncGenerator

import pytest
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from app.agents.runtime import run_workflow


class CancellationResistantAgent(BaseAgent):
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        del ctx
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            await asyncio.sleep(0.4)
        yield Event(author=self.name)


@pytest.mark.asyncio
async def test_workflow_timeout_does_not_wait_for_adk_cleanup():
    started = time.monotonic()

    with pytest.raises(TimeoutError):
        await run_workflow(
            CancellationResistantAgent(name="stubborn"),
            prompt="wait",
            outputs={},
            timeout=0.05,
        )

    assert time.monotonic() - started < 0.2
    await asyncio.sleep(0.5)
