"""Instruction templates and user-message assembly for the agents."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Literal

from ibikus.appa.agora.config import ConfigError
from ibikus.appa.agora.context import Context

from .critic import Critique

REVISE_INSTRUCTION = "Revise the previous draft to address every issue in the critique."


def load_instructions(role: Literal["generator", "critic"], override: Path | None) -> str:
    """Instructions from the override file, or the built-in template for the role."""
    if override is not None:
        try:
            return override.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise ConfigError(f"reflection.prompts.{role}: cannot read {override}: {e}") from e
    return (resources.files(__package__) / "templates" / f"{role}.md").read_text(encoding="utf-8")


def render_context(ctx: Context) -> str:
    blocks = [f"### file: {f.path.as_posix()}\n```\n{f.content}\n```" for f in ctx.files]
    return "\n\n".join(blocks)


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- (none)"


def _head(prompt: str, ctx: Context) -> list[str]:
    sections = []
    rendered = render_context(ctx)
    if rendered:
        sections.append(f"## Context\n{rendered}")
    sections.append(f"## Request\n{prompt}")
    return sections


def build_generator_input(
    prompt: str,
    ctx: Context,
    previous_draft: str | None = None,
    critique: Critique | None = None,
    language: str | None = None,
) -> str:
    sections = _head(prompt, ctx)
    if previous_draft is not None:
        sections.append(f"## Previous draft\n{previous_draft}")
        if critique is not None:
            sections.append(
                f"## Critique\nscore: {critique.score}\n\nFeedback: {critique.feedback}"
                f"\n\nIssues:\n{_bullets(critique.issues)}"
                f"\n\nSuggestions:\n{_bullets(critique.suggestions)}"
            )
        sections.append(REVISE_INSTRUCTION)
    if language:
        sections.append(f"Answer in {language}.")
    return "\n\n".join(sections)


def build_critic_input(
    prompt: str,
    ctx: Context,
    draft: str,
    threshold: int | None = None,
    truncated: bool = False,
    language: str | None = None,
) -> str:
    sections = [*_head(prompt, ctx), f"## Draft\n{draft}"]
    if truncated:
        sections.append("Note: the draft was cut off by the length limit before it was finished.")
    if threshold is not None:
        sections.append(
            "## Acceptance\n"
            f"The draft is accepted only with approved=true and a score of at least {threshold}. "
            "If you give a lower score, list in issues what prevents a higher score."
        )
    if language:
        sections.append(f"Write feedback, issues and suggestions in {language}.")
    return "\n\n".join(sections)
