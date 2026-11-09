"""Optional Langfuse tracing. Never breaks a run: failures degrade to a no-op."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from typing import Any, Literal, Protocol

from langfuse import Langfuse
from pydantic_ai import Agent

from ibikus.appa.agora.config import LangfuseConfig

logger = logging.getLogger(__name__)

ObservabilityState = Literal["off", "on", "error"]
Phase = Literal["generate", "critique"]


class SpanHandle(Protocol):
    def update(self, *, output: Any = None, metadata: dict[str, Any] | None = None) -> None: ...


class Observability(Protocol):
    state: ObservabilityState

    def run_span(
        self, prompt: str, metadata: dict[str, Any]
    ) -> AbstractContextManager[SpanHandle]: ...

    def iteration_span(
        self, iteration: int, phase: Phase
    ) -> AbstractContextManager[SpanHandle]: ...

    def flush(self) -> None: ...


class _NoopSpan:
    def update(self, *, output: Any = None, metadata: dict[str, Any] | None = None) -> None:
        return None


class NoopObservability:
    def __init__(self, state: ObservabilityState = "off") -> None:
        self.state: ObservabilityState = state

    @contextmanager
    def run_span(self, prompt: str, metadata: dict[str, Any]) -> Iterator[SpanHandle]:
        yield _NoopSpan()

    @contextmanager
    def iteration_span(self, iteration: int, phase: Phase) -> Iterator[SpanHandle]:
        yield _NoopSpan()

    def flush(self) -> None:
        return None


class _LangfuseSpan:
    def __init__(self, span: Any) -> None:
        self._span = span

    def update(self, *, output: Any = None, metadata: dict[str, Any] | None = None) -> None:
        try:
            self._span.update(output=output, metadata=metadata)
        except Exception:  # tracing must never break a run
            logger.warning("Langfuse span update failed", exc_info=True)


class LangfuseObservability:
    """One trace per run; one span per iteration phase; generations come from the
    Pydantic AI OpenTelemetry instrumentation and nest under the current span."""

    state: ObservabilityState = "on"

    def __init__(self, client: Any) -> None:
        self._client = client

    @contextmanager
    def run_span(self, prompt: str, metadata: dict[str, Any]) -> Iterator[SpanHandle]:
        with self._client.start_as_current_observation(
            name="reflection-run", as_type="agent", input=prompt, metadata=metadata
        ) as span:
            yield _LangfuseSpan(span)

    @contextmanager
    def iteration_span(self, iteration: int, phase: Phase) -> Iterator[SpanHandle]:
        with self._client.start_as_current_observation(
            name=f"iteration-{iteration}/{phase}",
            as_type="chain",
            metadata={"iteration": iteration, "phase": phase},
        ) as span:
            yield _LangfuseSpan(span)

    def flush(self) -> None:
        try:
            self._client.flush()
        except Exception:
            logger.warning("Langfuse flush failed", exc_info=True)


def setup_observability(cfg: LangfuseConfig, env: Mapping[str, str] | None = None) -> Observability:
    env = os.environ if env is None else env
    if cfg.enabled == "off":
        return NoopObservability("off")
    public, secret = env.get("LANGFUSE_PUBLIC_KEY"), env.get("LANGFUSE_SECRET_KEY")
    if not (public and secret):
        if cfg.enabled == "on":
            logger.warning("Langfuse enabled but LANGFUSE_PUBLIC_KEY/SECRET_KEY are not set")
            return NoopObservability("error")
        return NoopObservability("off")
    try:
        client = Langfuse(
            public_key=public, secret_key=secret, host=env.get("LANGFUSE_HOST") or None
        )
        Agent.instrument_all()
    except Exception:
        logger.warning("Langfuse initialisation failed; tracing disabled", exc_info=True)
        return NoopObservability("error")
    return LangfuseObservability(client)
