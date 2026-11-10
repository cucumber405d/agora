from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from ibikus.appa.agora.config import AppConfig, LangfuseConfig
from ibikus.appa.agora.context import Context
from ibikus.appa.agora.observability import langfuse as obs
from ibikus.appa.agora.observability.langfuse import setup_observability
from ibikus.appa.agora.reflection.events import RunFinished
from ibikus.appa.agora.reflection.service import ReflectionService

from ..reflection.fakes import c, make_agents

KEYS = {"LANGFUSE_PUBLIC_KEY": "pk", "LANGFUSE_SECRET_KEY": "sk"}


def test_off() -> None:
    assert setup_observability(LangfuseConfig(enabled="off"), env=KEYS).state == "off"


def test_auto_without_keys_is_off() -> None:
    assert setup_observability(LangfuseConfig(), env={}).state == "off"


def test_on_without_keys_is_error() -> None:
    assert setup_observability(LangfuseConfig(enabled="on"), env={}).state == "error"


def test_auto_with_keys_is_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(obs, "Langfuse", lambda **kw: object())
    monkeypatch.setattr(obs.Agent, "instrument_all", staticmethod(lambda *a, **k: None))
    assert setup_observability(LangfuseConfig(), env=KEYS).state == "on"


def test_init_failure_degrades(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(**kw: Any) -> None:
        raise RuntimeError("no server")

    monkeypatch.setattr(obs, "Langfuse", boom)
    assert setup_observability(LangfuseConfig(), env=KEYS).state == "error"


class _Span:
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name, self.calls = name, calls

    def update(self, *, output: Any = None, metadata: dict[str, Any] | None = None) -> None:
        self.calls.append(f"update:{self.name}:{sorted((metadata or {}).keys())}")


class FakeObservability:
    state = "on"

    def __init__(self) -> None:
        self.calls: list[str] = []

    @contextmanager
    def run_span(self, prompt: str, metadata: dict[str, Any]) -> Iterator[_Span]:
        self.calls.append("run")
        yield _Span("run", self.calls)

    @contextmanager
    def iteration_span(self, iteration: int, phase: str) -> Iterator[_Span]:
        self.calls.append(f"iter-{iteration}-{phase}")
        yield _Span(f"iter-{iteration}-{phase}", self.calls)

    def flush(self) -> None:
        pass


async def test_service_records_spans() -> None:
    rec = FakeObservability()
    svc = ReflectionService(
        AppConfig(), agents=make_agents(["A", "B"], [c(3), c(9, approved=True)]), observability=rec
    )
    events = [e async for e in svc.run("Q", Context.empty())]
    assert isinstance(events[-1], RunFinished)
    assert rec.calls == [
        "run",
        "iter-1-generate",
        "update:iter-1-generate:[]",
        "iter-1-critique",
        "update:iter-1-critique:['approved', 'score']",
        "iter-2-generate",
        "update:iter-2-generate:[]",
        "iter-2-critique",
        "update:iter-2-critique:['approved', 'score']",
        "update:run:['iterations', 'status']",
    ]
