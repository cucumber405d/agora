"""Test doubles: Agents backed by FunctionModel, no network."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Any

from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from ibikus.appa.agora.agents.critic import Critique, build_critic
from ibikus.appa.agora.agents.generator import build_generator
from ibikus.appa.agora.config import ReflectionConfig
from ibikus.appa.agora.context import Context
from ibikus.appa.agora.reflection.events import RunEvent
from ibikus.appa.agora.reflection.graph import Agents
from ibikus.appa.agora.reflection.state import ReflectionState, initial_state


class Recorder:
    def __init__(self) -> None:
        self.generator_inputs: list[str] = []


def _last_user_text(messages: list[ModelMessage]) -> str:
    return str(messages[-1])


def make_agents(
    drafts: Sequence[str | Exception],
    critiques: Sequence[Critique | Exception],
    *,
    chunk_delay: float = 0.0,
    recorder: Recorder | None = None,
) -> Agents:
    gen_calls = 0
    crit_calls = 0

    async def gen_stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
        nonlocal gen_calls
        item = drafts[min(gen_calls, len(drafts) - 1)]
        gen_calls += 1
        if recorder is not None:
            recorder.generator_inputs.append(_last_user_text(messages))
        if isinstance(item, Exception):
            raise item
        half = max(1, len(item) // 2)
        for i, piece in enumerate((item[:half], item[half:])):
            if i and chunk_delay:
                await asyncio.sleep(chunk_delay)
            if piece:
                yield piece

    def crit_fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal crit_calls
        item = critiques[min(crit_calls, len(critiques) - 1)]
        crit_calls += 1
        if isinstance(item, Exception):
            raise item
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, item.model_dump())])

    return Agents(
        generator=build_generator(FunctionModel(stream_function=gen_stream), {}, "gen"),
        critic=build_critic(FunctionModel(crit_fn), {}, "crit"),
        generator_settings={},
        critic_settings={},
    )


def cfg(**kw: Any) -> ReflectionConfig:
    return ReflectionConfig.model_validate(kw)


def c(score: int, approved: bool = False, issues: list[str] | None = None) -> Critique:
    return Critique(approved=approved, score=score, issues=issues or [])


async def collect(graph: Any, prompt: str) -> tuple[list[RunEvent], ReflectionState]:
    events: list[RunEvent] = []
    state: ReflectionState | None = None
    async for mode, payload in graph.astream(
        initial_state(prompt, Context.empty()), stream_mode=["custom", "values"]
    ):
        if mode == "custom":
            events.append(payload)
        else:
            state = payload
    assert state is not None
    return events, state
