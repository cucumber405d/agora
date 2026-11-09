"""Generator agent: writes (and revises) the answer as free Markdown text."""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings


def build_generator(model: Model, settings: ModelSettings, instructions: str) -> Agent[None, str]:
    return Agent(
        model, output_type=str, instructions=instructions, model_settings=settings, name="generator"
    )
