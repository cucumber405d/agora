import asyncio

import pytest
from pydantic_ai.exceptions import ModelConnectionError, UnexpectedModelBehavior

from ibikus.appa.agora.config import AppConfig, ConfigError
from ibikus.appa.agora.context import Context
from ibikus.appa.agora.reflection.events import DraftChunk, RunEvent, RunFailed, RunFinished
from ibikus.appa.agora.reflection.graph import Agents
from ibikus.appa.agora.reflection.service import ReflectionService

from .fakes import c, make_agents


def _svc(agents: Agents) -> ReflectionService:
    return ReflectionService(AppConfig(), agents=agents)


async def _all(svc: ReflectionService, prompt: str = "Q") -> list[RunEvent]:
    return [e async for e in svc.run(prompt, Context.empty())]


async def test_happy_path_ends_with_run_finished() -> None:
    events = await _all(_svc(make_agents(["AB"], [c(9, approved=True)])))
    last = events[-1]
    assert isinstance(last, RunFinished)
    assert last.result.status == "approved"
    assert last.result.final == "AB"
    assert any(isinstance(e, DraftChunk) for e in events)


async def test_empty_prompt() -> None:
    events = await _all(_svc(make_agents(["A"], [c(9)])), "   ")
    assert events == [RunFailed(reason="invalid_input", message="Prompt is empty")]


async def test_provider_error_becomes_run_failed() -> None:
    agents = make_agents([ModelConnectionError("m", "connection refused")], [c(9)])
    last = (await _all(_svc(agents)))[-1]
    assert isinstance(last, RunFailed)
    assert last.reason == "provider_error"
    assert "connection refused" in last.message


async def test_critic_invalid_becomes_run_failed() -> None:
    last = (await _all(_svc(make_agents(["A"], [UnexpectedModelBehavior("bad")]))))[-1]
    assert isinstance(last, RunFailed) and last.reason == "critic_invalid"


async def test_unexpected_exception_is_internal() -> None:
    last = (await _all(_svc(make_agents([RuntimeError("boom")], [c(9)]))))[-1]
    assert isinstance(last, RunFailed) and last.reason == "internal"
    assert "boom" in last.message


async def test_cancel_after_first_chunk() -> None:
    svc = _svc(make_agents(["AAAABBBB"], [c(9)], chunk_delay=10))
    cancel = asyncio.Event()
    events: list[RunEvent] = []
    async with asyncio.timeout(2):
        async for e in svc.run("Q", Context.empty(), cancel):
            events.append(e)
            if isinstance(e, DraftChunk):
                cancel.set()
    last = events[-1]
    assert isinstance(last, RunFailed) and last.reason == "cancelled"


def test_builds_agents_from_config_needs_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        ReflectionService(AppConfig())


def test_builds_agents_from_config_local_only() -> None:
    cfg = AppConfig.model_validate(
        {"reflection": {"critic": {"provider": "ollama", "name": "x", "temperature": 0.1}}}
    )
    assert ReflectionService(cfg).config is cfg
