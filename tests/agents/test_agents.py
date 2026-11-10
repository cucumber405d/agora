import json

import pytest
from pydantic import ValidationError
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from ibikus.appa.agora.agents.critic import Critique, build_critic
from ibikus.appa.agora.agents.generator import build_generator


async def test_critic_returns_typed_critique() -> None:
    agent = build_critic(TestModel(custom_output_args={"approved": True, "score": 9}), {}, "i")
    assert (await agent.run("x")).output == Critique(approved=True, score=9)


def _reply(info: AgentInfo, payload: dict[str, object] | str) -> ModelResponse:
    """Answer in whatever structured-output mode the agent requested."""
    if isinstance(payload, str):
        return ModelResponse(parts=[TextPart(payload)])
    if info.model_request_parameters.output_mode == "native":
        return ModelResponse(parts=[TextPart(json.dumps(payload))])
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, payload)])


async def test_critic_score_out_of_range_fails_after_retries() -> None:
    calls = 0

    def always_42(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        return _reply(info, {"approved": True, "score": 42})

    agent = build_critic(FunctionModel(always_42), {}, "i")
    with pytest.raises(UnexpectedModelBehavior):
        await agent.run("x")
    assert calls == 3  # first try + 2 output retries


async def test_critic_prose_answer_fails_after_retries() -> None:
    """qwen2.5:7b answered '**Approved:** true **Score:** 8' as Markdown instead of JSON."""

    def prose(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return _reply(info, "**Approved:** true\n**Score:** 8\n\nGood story.")

    with pytest.raises(UnexpectedModelBehavior):
        await build_critic(FunctionModel(prose), {}, "i").run("x")


def test_critique_rejects_echoed_validation_errors() -> None:
    """qwen2.5:7b copied the retry prompt ("Field 'approved' is required") into issues."""
    with pytest.raises(ValidationError):
        Critique.model_validate(
            {"approved": False, "score": 0, "issues": ["Field 'approved' is required"]}
        )


def test_critique_keeps_normal_issues() -> None:
    c = Critique.model_validate(
        {"approved": False, "score": 5, "issues": ["Field names are vague"]}
    )
    assert c.issues == ["Field names are vague"]


def test_output_mode_native_when_model_supports_json_schema() -> None:
    from pydantic_ai import NativeOutput

    from ibikus.appa.agora.agents.critic import critic_output

    assert isinstance(critic_output(FunctionModel(lambda m, i: None)), NativeOutput)
    assert critic_output(TestModel()) is Critique


async def test_critic_sends_json_schema_to_ollama() -> None:
    import httpx
    from openai import AsyncOpenAI
    from pydantic_ai.models.ollama import OllamaModel
    from pydantic_ai.providers.ollama import OllamaProvider

    bodies: list[dict[str, object]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(req.content))
        content = json.dumps({"approved": True, "score": 9})
        return httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "created": 0,
                "model": "m",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": content},
                    }
                ],
            },
        )

    client = AsyncOpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    model = OllamaModel("qwen2.5:7b", provider=OllamaProvider(openai_client=client))
    result = await build_critic(model, {}, "i").run("x")
    assert result.output == Critique(approved=True, score=9)
    fmt = bodies[0]["response_format"]
    assert isinstance(fmt, dict) and fmt["type"] == "json_schema"
    assert set(fmt["json_schema"]["schema"]["required"]) >= {"approved", "score"}
    assert not bodies[0].get("tools")


async def test_generator_streams_text() -> None:
    async def stream(messages: list[ModelMessage], info: AgentInfo):  # type: ignore[no-untyped-def]
        for chunk in ("he", "llo"):
            yield chunk

    agent = build_generator(FunctionModel(stream_function=stream), {}, "i")
    async with agent.run_stream("x") as result:
        deltas = [d async for d in result.stream_text(delta=True, debounce_by=None)]
    assert "".join(deltas) == "hello"
