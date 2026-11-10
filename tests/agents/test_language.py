import json

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from ibikus.appa.agora.agents.critic import Critique, build_critic
from ibikus.appa.agora.agents.language import detect_language
from ibikus.appa.agora.agents.prompts import build_critic_input, build_generator_input
from ibikus.appa.agora.context import Context


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("расскажи про меня сказку", "Russian"),
        ("Erzähl mir ein Märchen über mich", "German"),
        ("Was ist der Unterschied zwischen Prozess und Thread", "German"),
        ("Explain the difference between a process and a thread", "English"),
        ("", None),
        ("12345 ???", None),
    ],
)
def test_detect_language(text: str, expected: str | None) -> None:
    assert detect_language(text) == expected


def test_inputs_name_the_language() -> None:
    assert "Answer in Russian." in build_generator_input("Q", Context.empty(), language="Russian")
    critic = build_critic_input("Q", Context.empty(), "D", threshold=9, language="Russian")
    assert "Write feedback, issues and suggestions in Russian." in critic
    assert "Answer in" not in build_generator_input("Q", Context.empty())


def _verdict(feedback: str) -> str:
    return json.dumps(
        {"approved": False, "score": 6, "feedback": feedback, "issues": ["x"], "suggestions": []}
    )


async def test_critic_asked_once_to_switch_to_russian() -> None:
    answers = iter([_verdict("The story is fine."), _verdict("Сказка в целом хорошая.")])
    calls = 0

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        return ModelResponse(parts=[TextPart(next(answers))])

    result = await build_critic(FunctionModel(fn), {}, "i").run("x", deps="Russian")
    assert calls == 2
    assert result.output.feedback == "Сказка в целом хорошая."


async def test_wrong_language_accepted_after_one_retry() -> None:
    calls = 0

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        return ModelResponse(parts=[TextPart(_verdict("Still English."))])

    result = await build_critic(FunctionModel(fn), {}, "i").run("x", deps="Russian")
    assert calls == 2  # one retry, then the verdict is kept rather than lost
    assert isinstance(result.output, Critique)


async def test_no_language_check_without_deps() -> None:
    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(_verdict("English is fine."))])

    result = await build_critic(FunctionModel(fn), {}, "i").run("x")
    assert result.output.feedback == "English is fine."
