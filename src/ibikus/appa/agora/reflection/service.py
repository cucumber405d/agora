"""ReflectionService: the single entry point to the core for any UI."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior

from ibikus.appa.agora.agents.critic import build_critic
from ibikus.appa.agora.agents.generator import build_generator
from ibikus.appa.agora.agents.prompts import load_instructions
from ibikus.appa.agora.config import AppConfig
from ibikus.appa.agora.context import Context
from ibikus.appa.agora.llm.factory import build_model, build_settings, describe
from ibikus.appa.agora.observability.langfuse import NoopObservability, Observability

from .events import RunEvent, RunFailed, RunFinished
from .graph import Agents, build_graph, to_result
from .state import initial_state

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Failure:
    error: BaseException


class _Cancelled:
    pass


_QueueItem = RunEvent | _Failure | _Cancelled


def build_agents(config: AppConfig) -> Agents:
    """Build generator and critic from config. Raises ConfigError (e.g. missing API key)."""
    r = config.reflection
    return Agents(
        generator=build_generator(
            build_model(r.generator),
            build_settings(r.generator),
            load_instructions("generator", r.prompts.generator),
        ),
        critic=build_critic(
            build_model(r.critic),
            build_settings(r.critic),
            load_instructions("critic", r.prompts.critic),
        ),
        generator_settings=build_settings(r.generator),
        critic_settings=build_settings(r.critic),
    )


def _to_failure(error: BaseException) -> RunFailed:
    if isinstance(error, ModelAPIError):
        return RunFailed(reason="provider_error", message=str(error))
    if isinstance(error, UnexpectedModelBehavior):
        # The critic node handles its own failures, so this comes from the generator.
        return RunFailed(
            reason="generator_failed",
            message=(
                f"Generator produced no usable answer: {error} "
                "Hint: for thinking models (qwen3, qwen3.5) set think: false for the generator; "
                "otherwise raise OLLAMA_CONTEXT_LENGTH or mark fewer files."
            ),
        )
    logger.error("Reflection run failed", exc_info=error)
    return RunFailed(reason="internal", message=f"{type(error).__name__}: {error}")


class ReflectionService:
    def __init__(
        self,
        config: AppConfig,
        agents: Agents | None = None,
        observability: Observability | None = None,
    ) -> None:
        self._config = config
        self._obs: Observability = observability or NoopObservability()
        self._agents = agents if agents is not None else build_agents(config)
        self._graph = build_graph(self._agents, config.reflection, self._obs)

    @property
    def config(self) -> AppConfig:
        return self._config

    async def run(
        self, prompt: str, context: Context, cancel: asyncio.Event | None = None
    ) -> AsyncIterator[RunEvent]:
        """Run the reflection loop. Always ends with RunFinished or RunFailed."""
        if not prompt.strip():
            yield RunFailed(reason="invalid_input", message="Prompt is empty")
            return

        queue: asyncio.Queue[_QueueItem] = asyncio.Queue()

        r = self._config.reflection
        span_meta = {"generator": describe(r.generator), "critic": describe(r.critic)}

        async def pump() -> None:
            try:
                with self._obs.run_span(prompt, span_meta) as span:
                    state = None
                    async for mode, payload in self._graph.astream(
                        initial_state(prompt, context), stream_mode=["custom", "values"]
                    ):
                        if mode == "custom":
                            queue.put_nowait(payload)
                        else:
                            state = payload
                    assert state is not None
                    result = to_result(state, r)
                    span.update(
                        output=result.final,
                        metadata={"status": result.status, "iterations": result.iterations},
                    )
                queue.put_nowait(RunFinished(result=result))
            except asyncio.CancelledError:
                raise
            except Exception as e:
                queue.put_nowait(_Failure(e))

        async def watch_cancel(event: asyncio.Event) -> None:
            await event.wait()
            queue.put_nowait(_Cancelled())

        tasks = [asyncio.create_task(pump())]
        if cancel is not None:
            tasks.append(asyncio.create_task(watch_cancel(cancel)))
        try:
            while True:
                item = await queue.get()
                if isinstance(item, _Cancelled):
                    yield RunFailed(reason="cancelled", message="Run cancelled")
                    return
                if isinstance(item, _Failure):
                    yield _to_failure(item.error)
                    return
                yield item
                if isinstance(item, RunFinished):
                    return
        finally:
            for t in tasks:
                t.cancel()
            for t in tasks:
                with contextlib.suppress(asyncio.CancelledError):
                    await t
