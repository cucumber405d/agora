"""Critic agent: reviews a draft and returns a structured verdict."""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent, AgentRetries
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings


class Critique(BaseModel):
    approved: bool
    score: int = Field(ge=0, le=10)
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


def build_critic(model: Model, settings: ModelSettings, instructions: str) -> Agent[None, Critique]:
    return Agent(
        model,
        output_type=Critique,
        instructions=instructions,
        model_settings=settings,
        retries=AgentRetries(output=2),
        name="critic",
    )
