"""Context data passed to the agents."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token). Offline, provider-independent."""
    return math.ceil(len(text) / 4)


class ContextFile(BaseModel):
    path: Path
    content: str
    tokens: int
    source_format: str | None = None  # "PDF", "DOCX", ... when converted from a document


SkipReason = Literal[
    "extension",
    "too_large",
    "not_utf8",
    "over_budget",
    "unreadable",
    "legacy_format",
    "no_text",
    "convert_failed",
]


class SkippedFile(BaseModel):
    path: Path
    reason: SkipReason


class Context(BaseModel):
    files: list[ContextFile] = Field(default_factory=list)
    skipped: list[SkippedFile] = Field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(f.tokens for f in self.files)

    @classmethod
    def empty(cls) -> Context:
        return cls()
