"""Build provider-specific Pydantic AI models from ModelConfig."""

from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic_ai.exceptions import UserError
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.settings import ModelSettings

from ibikus.appa.agora.config import ConfigError, ModelConfig, Provider

DEFAULT_OLLAMA_URL = "http://localhost:11434/v1"

_ENV_KEYS: dict[Provider, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def required_env_key(provider: Provider) -> str | None:
    """Name of the env variable holding the provider's API key (None for local Ollama)."""
    return _ENV_KEYS.get(provider)


def _api_key(provider: Provider, env: Mapping[str, str]) -> str:
    key_name = _ENV_KEYS[provider]
    value = env.get(key_name, "").strip()
    if not value:
        raise ConfigError(f"{key_name} is not set (needed for provider '{provider}')")
    return value


def build_model(cfg: ModelConfig, env: Mapping[str, str] | None = None) -> Model:
    """Create the Pydantic AI model for cfg. Raises ConfigError if an API key is missing
    or the provider rejects the model settings."""
    try:
        return _build(cfg, os.environ if env is None else env)
    except UserError as e:
        raise ConfigError(f"{cfg.provider}/{cfg.name}: {e}") from e


def _build(cfg: ModelConfig, env: Mapping[str, str]) -> Model:
    match cfg.provider:
        case "ollama":
            return OllamaModel(
                cfg.name, provider=OllamaProvider(base_url=cfg.base_url or DEFAULT_OLLAMA_URL)
            )
        case "anthropic":
            return AnthropicModel(
                cfg.name, provider=AnthropicProvider(api_key=_api_key("anthropic", env))
            )
        case "openai":
            return OpenAIChatModel(
                cfg.name,
                provider=OpenAIProvider(api_key=_api_key("openai", env), base_url=cfg.base_url),
            )
        case "openrouter":
            return OpenRouterModel(
                cfg.name, provider=OpenRouterProvider(api_key=_api_key("openrouter", env))
            )


def build_settings(cfg: ModelConfig) -> ModelSettings:
    """Per-call settings: temperature, timeout and SDK-level retries with backoff."""
    settings = ModelSettings(
        temperature=cfg.temperature, timeout=cfg.timeout_s, max_retries=cfg.max_retries
    )
    if cfg.max_tokens is not None:
        settings["max_tokens"] = cfg.max_tokens
    return settings


def describe(cfg: ModelConfig) -> str:
    """Short label for the status line, e.g. 'ollama/qwen2.5:7b t=0.9'."""
    return f"{cfg.provider}/{cfg.name} t={cfg.temperature:g}"
