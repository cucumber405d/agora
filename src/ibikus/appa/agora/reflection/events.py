"""Events emitted by a reflection run; the only contract between core and UI."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from ibikus.appa.agora.agents.critic import Critique


class IterationRecord(BaseModel):
    iteration: int
    draft: str
    critique: Critique


class RunResult(BaseModel):
    final: str
    status: Literal["approved", "max_iterations", "critic_failed"]
    iterations: int
    best_score: int
    history: list[IterationRecord]


class IterationStarted(BaseModel):
    kind: Literal["iteration_started"] = "iteration_started"
    iteration: int
    max_iterations: int


class DraftChunk(BaseModel):
    kind: Literal["draft_chunk"] = "draft_chunk"
    iteration: int
    text: str


class DraftDone(BaseModel):
    kind: Literal["draft_done"] = "draft_done"
    iteration: int
    text: str
    truncated: bool = False  # generation stopped at the token/context limit


class CritiqueDone(BaseModel):
    kind: Literal["critique_done"] = "critique_done"
    iteration: int
    critique: Critique


class CritiqueFailed(BaseModel):
    """The critic could not produce a valid verdict; the run finishes with the latest draft."""

    kind: Literal["critique_failed"] = "critique_failed"
    iteration: int
    message: str


class RunFinished(BaseModel):
    kind: Literal["run_finished"] = "run_finished"
    result: RunResult


FailReason = Literal["cancelled", "provider_error", "generator_failed", "invalid_input", "internal"]


class RunFailed(BaseModel):
    kind: Literal["run_failed"] = "run_failed"
    reason: FailReason
    message: str


RunEvent = Annotated[
    IterationStarted
    | DraftChunk
    | DraftDone
    | CritiqueDone
    | CritiqueFailed
    | RunFinished
    | RunFailed,
    Field(discriminator="kind"),
]
