"""Critic agent: reviews a draft and returns a structured verdict."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_ai import Agent, AgentRetries, ModelRetry, NativeOutput, RunContext
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from .language import cyrillic_share

# Small models sometimes echo the retry prompt ("Field 'score' is required") into the verdict.
_ECHOED_VALIDATION = re.compile(
    r"field '?\w+'? (is )?required|validation error|input should be", re.IGNORECASE
)


MIN_APPROVED_SCORE = 5


class Critique(BaseModel):
    approved: bool = Field(description="True only if the draft has no material issues.")
    score: int = Field(ge=0, le=10, description="Quality from 0 (useless) to 10 (excellent).")
    feedback: str = Field(
        description="Overall assessment in 1-3 sentences; always required, also when approved."
    )
    issues: list[str] = Field(
        default_factory=list, description="Concrete problems in the draft; empty if approved."
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Concrete, actionable improvements."
    )

    @model_validator(mode="after")
    def _consistent_verdict(self) -> Critique:
        if self.approved and self.score < MIN_APPROVED_SCORE:
            raise ValueError(
                f"approved=true with score {self.score} is inconsistent; "
                f"approve only drafts scoring {MIN_APPROVED_SCORE} or more"
            )
        if not self.approved and not self.issues:
            raise ValueError("issues must list what prevents approval when approved=false")
        return self

    @field_validator("feedback")
    @classmethod
    def _feedback_is_real_text(cls, text: str) -> str:
        text = text.strip()
        if not text:
            raise ValueError("feedback must not be empty")
        _reject_echo(text)
        return text

    @field_validator("issues", "suggestions")
    @classmethod
    def _no_echoed_validation_errors(cls, items: list[str]) -> list[str]:
        for item in items:
            _reject_echo(item)
        return items


def _reject_echo(text: str) -> None:
    if _ECHOED_VALIDATION.search(text):
        raise ValueError(
            f"must describe the draft, not the response format; got a validation message: {text!r}"
        )


def critic_output(model: Model) -> type[Critique] | NativeOutput[Critique]:
    """Prefer a JSON-schema constrained response (reliable even for small local models);
    fall back to tool-call output for models without JSON-schema support."""
    if model.profile.get("supports_json_schema_output", False):
        return NativeOutput(Critique)
    return Critique


CriticDeps = str | None  # expected language of the verdict, e.g. "Russian"


def build_critic(
    model: Model, settings: ModelSettings, instructions: str
) -> Agent[CriticDeps, Critique]:
    agent: Agent[CriticDeps, Critique] = Agent(
        model,
        output_type=critic_output(model),
        instructions=instructions,
        model_settings=settings,
        retries=AgentRetries(output=2),
        deps_type=CriticDeps,
        name="critic",
    )

    @agent.output_validator
    def _expected_language(ctx: RunContext[CriticDeps], verdict: Critique) -> Critique:
        # Only Cyrillic can be checked reliably by script; ask once, then keep the verdict.
        if ctx.deps == "Russian" and ctx.retry == 0 and cyrillic_share(verdict.feedback) < 0.5:
            raise ModelRetry("Write feedback, issues and suggestions in Russian.")
        return verdict

    return agent
