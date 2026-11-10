"""Turn Pydantic AI message history into LlmExchange events for the LLM log."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryFeedbackPart,
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
)

from ibikus.appa.agora.context import estimate_tokens

from .events import LlmExchange

Role = Literal["generator", "critic"]


def model_label(agent: Any) -> str:
    model = getattr(agent, "model", None)
    return str(getattr(model, "model_name", model))


def request_exchange(role: Role, model: str, instructions: str, user_input: str) -> LlmExchange:
    text = (
        f"[instructions]\n{instructions}\n\n[input]\n{user_input}" if instructions else user_input
    )
    return LlmExchange(
        role=role, direction="request", model=model, text=text, tokens=estimate_tokens(text)
    )


def _response_text(msg: ModelResponse) -> str:
    out = []
    for part in msg.parts:
        if isinstance(part, TextPart):
            out.append(part.content)
        elif isinstance(part, ToolCallPart):
            out.append(part.args_as_json_str())
        elif isinstance(part, ThinkingPart):
            out.append(f"(thinking: {len(part.content)} chars)")
    return "\n".join(out)


def exchanges_after_request(
    role: Role,
    model: str,
    messages: Sequence[ModelMessage],
    seconds: float | None = None,
    failed: bool = False,
) -> list[LlmExchange]:
    """Responses and retry requests that followed the first request (already logged live).
    `seconds` (wall time of the whole call) is attached to the last response. With `failed`,
    empty placeholder responses left behind by an aborted call are dropped."""
    out: list[LlmExchange] = []
    for msg in messages[1:]:
        if isinstance(msg, ModelResponse):
            if failed and not _response_text(msg):
                continue
            out.append(
                LlmExchange(
                    role=role,
                    direction="response",
                    model=model,
                    text=_response_text(msg),
                    tokens=msg.usage.output_tokens or None,
                    finish=msg.finish_reason,
                )
            )
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                # Validation feedback (RetryFeedbackPart) and tool retries (RetryPromptPart).
                if isinstance(part, RetryFeedbackPart | RetryPromptPart):
                    out.append(
                        LlmExchange(
                            role=role, direction="retry", model=model, text=part.model_response()
                        )
                    )
    responses = [i for i, e in enumerate(out) if e.direction == "response"]
    if responses and seconds is not None:
        out[responses[-1]] = out[responses[-1]].model_copy(update={"seconds": seconds})
    return out


def error_exchange(role: Role, model: str, error: BaseException) -> LlmExchange:
    return LlmExchange(
        role=role, direction="error", model=model, text=f"{type(error).__name__}: {error}"
    )
