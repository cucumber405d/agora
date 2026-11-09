import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from ibikus.appa.agora.agents.critic import Critique, build_critic
from ibikus.appa.agora.agents.generator import build_generator


async def test_critic_returns_typed_critique() -> None:
    agent = build_critic(TestModel(custom_output_args={"approved": True, "score": 9}), {}, "i")
    assert (await agent.run("x")).output == Critique(approved=True, score=9)


async def test_critic_score_out_of_range_fails_after_retries() -> None:
    calls = 0

    def always_42(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        tool = info.output_tools[0].name
        return ModelResponse(parts=[ToolCallPart(tool, {"approved": True, "score": 42})])

    agent = build_critic(FunctionModel(always_42), {}, "i")
    with pytest.raises(UnexpectedModelBehavior):
        await agent.run("x")
    assert calls == 3  # first try + 2 output retries


async def test_generator_streams_text() -> None:
    async def stream(messages: list[ModelMessage], info: AgentInfo):  # type: ignore[no-untyped-def]
        for chunk in ("he", "llo"):
            yield chunk

    agent = build_generator(FunctionModel(stream_function=stream), {}, "i")
    async with agent.run_stream("x") as result:
        deltas = [d async for d in result.stream_text(delta=True, debounce_by=None)]
    assert "".join(deltas) == "hello"
