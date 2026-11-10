"""Lightweight reachability checks for the configured LLM endpoints.

Each distinct endpoint is probed once with a short timeout; the result is a list of
human-readable issues (what is wrong, how to fix it) grouped by the roles affected.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from ibikus.appa.agora.config import AppConfig, ModelConfig

from .factory import DEFAULT_OLLAMA_URL, required_env_key

DEFAULT_TIMEOUT_S = 3.0

_CLOUD_URLS = {
    "anthropic": "https://api.anthropic.com/v1/models",
    "openai": "https://api.openai.com/v1/models",
    "openrouter": "https://openrouter.ai/api/v1/key",
}


@dataclass(frozen=True)
class HealthIssue:
    roles: tuple[str, ...]
    problem: str
    hint: str


@dataclass(frozen=True)
class _Probe:
    provider: str
    url: str
    headers: tuple[tuple[str, str], ...]
    key_name: str | None


def _ollama_host(cfg: ModelConfig) -> str:
    url = (cfg.base_url or DEFAULT_OLLAMA_URL).rstrip("/")
    return url.removesuffix("/v1")


def _probe(cfg: ModelConfig, key: str | None) -> _Probe:
    if cfg.provider == "ollama":
        return _Probe("ollama", f"{_ollama_host(cfg)}/api/tags", (), None)
    key_name = required_env_key(cfg.provider)
    if cfg.provider == "anthropic":
        headers: tuple[tuple[str, str], ...] = (
            ("x-api-key", key or ""),
            ("anthropic-version", "2023-06-01"),
        )
        url = _CLOUD_URLS["anthropic"]
    else:
        headers = (("authorization", f"Bearer {key}"),)
        url = _CLOUD_URLS[cfg.provider]
        if cfg.provider == "openai" and cfg.base_url:
            url = f"{cfg.base_url.rstrip('/')}/models"
    return _Probe(cfg.provider, url, headers, key_name)


def _model_present(name: str, available: list[str]) -> bool:
    return name in available or (":" not in name and f"{name}:latest" in available)


async def _fetch(client: httpx.AsyncClient, probe: _Probe) -> httpx.Response | Exception:
    try:
        return await client.get(probe.url, headers=dict(probe.headers))
    except (httpx.HTTPError, OSError) as e:
        return e


def _evaluate(
    probe: _Probe, roles: list[tuple[str, ModelConfig]], result: httpx.Response | Exception
) -> list[HealthIssue]:
    names = tuple(role for role, _ in roles)
    host = urlsplit(probe.url).netloc
    if probe.provider == "ollama":
        base = probe.url.removesuffix("/api/tags")
        if isinstance(result, Exception):
            return [
                HealthIssue(
                    names,
                    f"Ollama is not reachable at {base}",
                    "Install Ollama from https://ollama.com and start it (ollama serve). "
                    "If it runs on another host, set base_url in config/agora.yaml.",
                )
            ]
        if result.status_code != 200:
            return [
                HealthIssue(
                    names,
                    f"Ollama at {base} answered HTTP {result.status_code}",
                    "Check the Ollama server log.",
                )
            ]
        available = [m.get("name", "") for m in result.json().get("models", [])]
        issues = []
        for model in dict.fromkeys(cfg.name for _, cfg in roles):
            if not _model_present(model, available):
                affected = tuple(role for role, cfg in roles if cfg.name == model)
                issues.append(
                    HealthIssue(
                        affected,
                        f"Model '{model}' is not available in Ollama",
                        f"Run: ollama pull {model}",
                    )
                )
        return issues
    if isinstance(result, Exception):
        return [
            HealthIssue(
                names,
                f"No connection to {host}",
                "Check the internet connection and proxy settings.",
            )
        ]
    if result.status_code in (401, 403):
        return [
            HealthIssue(
                names,
                f"{probe.key_name} was rejected (HTTP {result.status_code})",
                f"Check {probe.key_name} in .env.",
            )
        ]
    if result.status_code >= 400:
        return [
            HealthIssue(
                names,
                f"{host} answered HTTP {result.status_code}",
                "Try again later or check the provider status page.",
            )
        ]
    return []


async def check_models(
    roles: Mapping[str, ModelConfig],
    env: Mapping[str, str] | None = None,
    client: httpx.AsyncClient | None = None,
    request_timeout_s: float = DEFAULT_TIMEOUT_S,
) -> list[HealthIssue]:
    """Probe every distinct endpoint used by the given roles once and report problems."""
    env = os.environ if env is None else env
    issues: list[HealthIssue] = []
    groups: dict[_Probe, list[tuple[str, ModelConfig]]] = {}
    missing_keys: dict[str, list[str]] = {}
    for role, cfg in roles.items():
        key_name = required_env_key(cfg.provider)
        key = env.get(key_name, "").strip() if key_name else None
        if key_name and not key:
            missing_keys.setdefault(key_name, []).append(role)
            continue
        groups.setdefault(_probe(cfg, key), []).append((role, cfg))
    for key_name, affected in missing_keys.items():
        issues.append(
            HealthIssue(
                tuple(affected),
                f"{key_name} is not set",
                f"Add {key_name}=... to .env or switch the model (F9).",
            )
        )
    if not groups:
        return issues
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=request_timeout_s)
    try:
        for probe, members in groups.items():
            issues.extend(_evaluate(probe, members, await _fetch(http, probe)))
    finally:
        if own_client:
            await http.aclose()
    return issues


async def check_config(config: AppConfig) -> list[HealthIssue]:
    """Check generator and critic of an AppConfig."""
    r = config.reflection
    return await check_models({"Generator": r.generator, "Critic": r.critic})
