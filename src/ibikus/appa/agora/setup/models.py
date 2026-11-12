"""Pull the preset's models into Ollama and verify that they run as expected."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import httpx

from .diagnostics import Check, parse_ollama_ps
from .presets import Preset
from .runner import Runner


class PullError(Exception):
    """Ollama refused or did not finish a pull."""


@dataclass(frozen=True)
class PullProgress:
    model: str
    status: str
    completed: int | None = None
    total: int | None = None


def _normalize(name: str) -> str:
    return name if ":" in name else f"{name}:latest"


def same_model(a: str, b: str) -> bool:
    return _normalize(a) == _normalize(b)


def missing_models(preset: Preset, installed: Sequence[str]) -> list[str]:
    return [m for m in preset.models if not any(same_model(m, i) for i in installed)]


async def pull(model: str, client: httpx.AsyncClient, base_url: str) -> AsyncIterator[PullProgress]:
    """Stream `POST /api/pull`. Cancel by cancelling the consuming task; Ollama resumes
    partially downloaded layers on the next pull."""
    done = False
    try:
        async with client.stream(
            "POST", f"{base_url}/api/pull", json={"model": model, "stream": True}, timeout=None
        ) as response:
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except ValueError as e:
                    raise PullError(f"unexpected answer from Ollama: {line[:200]}") from e
                if not isinstance(item, dict):
                    raise PullError(f"unexpected answer from Ollama: {line[:200]}")
                if "error" in item:
                    raise PullError(str(item["error"]))
                status = str(item.get("status", ""))
                yield PullProgress(model, status, item.get("completed"), item.get("total"))
                done = done or status == "success"
    except httpx.HTTPError as e:
        raise PullError(f"{type(e).__name__}: {e}") from e
    if not done:
        raise PullError("interrupted")


async def verify(
    preset: Preset, client: httpx.AsyncClient, base_url: str, runner: Runner, ollama_exe: Path
) -> list[Check]:
    """Load the generator with a 1-token request, then check `ollama ps` for GPU and context."""
    model = preset.generator
    try:
        r = await client.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": "ok", "stream": False, "options": {"num_predict": 1}},
            timeout=300,
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        try:
            detail = str(e.response.json().get("error", e))
        except ValueError:
            detail = str(e)
        return [Check("Model", "error", f"{model}: {detail}")]
    except httpx.HTTPError as e:
        return [Check("Model", "error", f"{model}: {e}")]
    checks = [Check("Model", "ok", f"{model} loaded")]
    res = runner([str(ollama_exe), "ps"], 10)
    loaded = next((m for m in parse_ollama_ps(res.stdout) if same_model(m.name, model)), None)
    if res.returncode != 0 or loaded is None:
        checks.append(Check("Processor", "warn", "`ollama ps` did not list the model"))
        return checks
    on_gpu = loaded.processor == "100% GPU"
    checks.append(
        Check(
            "Processor",
            "ok" if on_gpu else "warn",
            loaded.processor
            if on_gpu
            else f"{loaded.processor}: part of the model runs on the CPU (slow)",
        )
    )
    ctx_ok = loaded.context is not None and loaded.context >= preset.ollama_context
    checks.append(
        Check(
            "Context",
            "ok" if ctx_ok else "warn",
            f"{loaded.context}"
            if ctx_ok
            else f"{loaded.context} < {preset.ollama_context}: restart Ollama to apply the setting",
        )
    )
    return checks
