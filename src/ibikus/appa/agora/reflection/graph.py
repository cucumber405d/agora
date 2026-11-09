"""generate -> critique -> (generate | finalize) loop on LangGraph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.settings import ModelSettings

from ibikus.appa.agora.agents.critic import Critique
from ibikus.appa.agora.agents.prompts import build_critic_input, build_generator_input
from ibikus.appa.agora.config import ReflectionConfig
from ibikus.appa.agora.observability.langfuse import NoopObservability, Observability

from .events import (
    CritiqueDone,
    DraftChunk,
    DraftDone,
    IterationRecord,
    IterationStarted,
    RunResult,
)
from .state import ReflectionState


@dataclass(frozen=True)
class Agents:
    generator: Agent[None, str]
    critic: Agent[None, Critique]
    generator_settings: ModelSettings
    critic_settings: ModelSettings


class CriticInvalidError(Exception):
    """The critic did not return a valid Critique even after output retries."""


def is_approved(c: Critique, threshold: int) -> bool:
    return c.approved or c.score >= threshold


def route(state: ReflectionState, cfg: ReflectionConfig) -> Literal["generate", "finalize"]:
    if is_approved(state["critiques"][-1], cfg.approve_threshold):
        return "finalize"
    if state["iteration"] >= cfg.max_iterations:
        return "finalize"
    return "generate"


def select_final(drafts: list[str], critiques: list[Critique], approved: bool) -> tuple[str, int]:
    """Last draft when approved; otherwise the highest-scored one (later wins ties)."""
    if approved:
        idx = len(drafts) - 1
    else:
        idx = max(range(len(drafts)), key=lambda i: (critiques[i].score, i))
    return drafts[idx], idx


def to_result(state: ReflectionState, cfg: ReflectionConfig) -> RunResult:
    drafts, critiques = state["drafts"], state["critiques"]
    approved = is_approved(critiques[-1], cfg.approve_threshold)
    final, idx = select_final(drafts, critiques, approved)
    return RunResult(
        final=final,
        status="approved" if approved else "max_iterations",
        iterations=state["iteration"],
        best_score=critiques[idx].score,
        history=[
            IterationRecord(iteration=i + 1, draft=d, critique=k)
            for i, (d, k) in enumerate(zip(drafts, critiques, strict=True))
        ],
    )


def build_graph(
    agents: Agents, cfg: ReflectionConfig, observability: Observability | None = None
) -> Any:
    """Compile the reflection graph. Nodes emit RunEvents via the custom stream mode."""
    obs: Observability = observability or NoopObservability()

    async def generate(state: ReflectionState) -> dict[str, Any]:
        write = get_stream_writer()
        n = state["iteration"] + 1
        write(IterationStarted(iteration=n, max_iterations=cfg.max_iterations))
        previous = state["drafts"][-1] if state["drafts"] else None
        critique = state["critiques"][-1] if state["critiques"] else None
        user_input = build_generator_input(state["prompt"], state["context"], previous, critique)
        parts: list[str] = []
        with obs.iteration_span(n, "generate") as span:
            async with agents.generator.run_stream(
                user_input, model_settings=agents.generator_settings
            ) as result:
                async for delta in result.stream_text(delta=True, debounce_by=None):
                    parts.append(delta)
                    write(DraftChunk(iteration=n, text=delta))
            draft = "".join(parts)
            span.update(output=draft)
        write(DraftDone(iteration=n, text=draft))
        return {"iteration": n, "drafts": [*state["drafts"], draft]}

    async def critique(state: ReflectionState) -> dict[str, Any]:
        write = get_stream_writer()
        user_input = build_critic_input(state["prompt"], state["context"], state["drafts"][-1])
        with obs.iteration_span(state["iteration"], "critique") as span:
            try:
                run = await agents.critic.run(user_input, model_settings=agents.critic_settings)
            except UnexpectedModelBehavior as e:
                raise CriticInvalidError(str(e)) from e
            span.update(
                output=run.output.model_dump(),
                metadata={"score": run.output.score, "approved": run.output.approved},
            )
        write(CritiqueDone(iteration=state["iteration"], critique=run.output))
        return {"critiques": [*state["critiques"], run.output]}

    async def finalize(state: ReflectionState) -> dict[str, Any]:
        return {}

    g: StateGraph[ReflectionState] = StateGraph(ReflectionState)
    g.add_node("generate", generate)
    g.add_node("critique", critique)
    g.add_node("finalize", finalize)
    g.add_edge(START, "generate")
    g.add_edge("generate", "critique")
    g.add_conditional_edges("critique", lambda s: route(s, cfg), ["generate", "finalize"])
    g.add_edge("finalize", END)
    return g.compile()
