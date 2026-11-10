"""LangGraph state of a reflection run."""

from __future__ import annotations

from typing import TypedDict

from ibikus.appa.agora.agents.critic import Critique
from ibikus.appa.agora.context import Context


class ReflectionState(TypedDict):
    prompt: str
    context: Context
    iteration: int
    drafts: list[str]
    critiques: list[Critique]
    critic_error: str | None


def initial_state(prompt: str, context: Context) -> ReflectionState:
    return ReflectionState(
        prompt=prompt, context=context, iteration=0, drafts=[], critiques=[], critic_error=None
    )
