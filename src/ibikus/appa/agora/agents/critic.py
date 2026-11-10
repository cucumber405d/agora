"""Critic agent: reviews a draft and returns a structured verdict."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent, AgentRetries, NativeOutput
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

# Small models sometimes echo the retry prompt ("Field 'score' is required") into the verdict.
_ECHOED_VALIDATION = re.compile(
    r"field '?\w+'? (is )?required|validation error|input should be", re.IGNORECASE
)


class Critique(BaseModel):
    approved: bool = Field(description="True only if the draft has no material issues.")
    score: int = Field(ge=0, le=10, description="Quality from 0 (useless) to 10 (excellent).")
    issues: list[str] = Field(
        default_factory=list, description="Concrete problems in the draft; empty if approved."
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Concrete, actionable improvements."
    )

    @field_validator("issues", "suggestions")
    @classmethod
    def _no_echoed_validation_errors(cls, items: list[str]) -> list[str]:
        for item in items:
            if _ECHOED_VALIDATION.search(item):
                raise ValueError(
                    "must describe the draft, not the response format; "
                    f"got a validation message: {item!r}"
                )
        return items


def critic_output(model: Model) -> type[Critique] | NativeOutput[Critique]:
    """Prefer a JSON-schema constrained response (reliable even for small local models);
    fall back to tool-call output for models without JSON-schema support."""
    if model.profile.get("supports_json_schema_output", False):
        return NativeOutput(Critique)
    return Critique


def build_critic(model: Model, settings: ModelSettings, instructions: str) -> Agent[None, Critique]:
    return Agent(
        model,
        output_type=critic_output(model),
        instructions=instructions,
        model_settings=settings,
        retries=AgentRetries(output=2),
        name="critic",
    )
