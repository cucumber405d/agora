"""Configuration models for Agora."""

from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

Provider = Literal["ollama", "anthropic", "openai", "openrouter"]

# Set by load_config() for the duration of a single AppConfig construction.
_yaml_path: ContextVar[Path | None] = ContextVar("agora_yaml_path", default=None)
_env_mapping: ContextVar[dict[str, str] | None] = ContextVar("agora_env_mapping", default=None)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelConfig(_Strict):
    """One LLM endpoint. API keys are never part of the config; they come from env."""

    provider: Provider
    name: str
    temperature: float = Field(ge=0, le=2)
    max_tokens: int | None = None
    base_url: str | None = None
    timeout_s: float = 60
    max_retries: int = 3
    # Ollama thinking models (qwen3, qwen3.5, ...): False disables the reasoning phase,
    # None keeps the model default. Ignored for cloud providers.
    think: bool | None = None


class PromptsConfig(_Strict):
    """Paths to instruction templates; None means the built-in template."""

    generator: Path | None = None
    critic: Path | None = None


def _default_generator() -> ModelConfig:
    return ModelConfig(
        provider="ollama",
        name="qwen2.5:7b",
        temperature=0.9,
        base_url="http://localhost:11434/v1",
    )


def _default_critic() -> ModelConfig:
    return ModelConfig(provider="anthropic", name="claude-haiku-4-5", temperature=0.1)


class ReflectionConfig(_Strict):
    max_iterations: int = Field(3, ge=1, le=10)
    approve_threshold: int = Field(8, ge=0, le=10)
    generator: ModelConfig = Field(default_factory=_default_generator)
    critic: ModelConfig = Field(default_factory=_default_critic)
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)

    @model_validator(mode="before")
    @classmethod
    def _fill_role_defaults(cls, data: Any) -> Any:
        """Partial overrides (e.g. only critic.temperature) keep the role's defaults, but only
        while the provider stays the default one: switching provider must not inherit the old
        model name or Ollama base_url."""
        if not isinstance(data, dict):
            return data
        data = dict(data)
        for role, default_factory in (
            ("generator", _default_generator),
            ("critic", _default_critic),
        ):
            given = data.get(role)
            if isinstance(given, dict):
                default = default_factory().model_dump(exclude_none=True)
                if given.get("provider", default["provider"]) == default["provider"]:
                    data[role] = {**default, **given}
        return data


class ContextConfig(_Strict):
    max_file_kb: int = Field(256, ge=1)
    max_total_tokens: int = Field(32000, ge=1)
    allowed_ext: list[str] = Field(
        default_factory=lambda: [".md", ".txt", ".py", ".java", ".yaml", ".json"]
    )


class LangfuseConfig(_Strict):
    enabled: Literal["auto", "on", "off"] = "auto"


class ObservabilityConfig(_Strict):
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)


class _MappingEnvSource(EnvSettingsSource):
    """Env source that reads from an explicit mapping instead of os.environ."""

    def __init__(self, settings_cls: type[BaseSettings], mapping: dict[str, str]) -> None:
        self._mapping = mapping
        super().__init__(settings_cls)

    def _load_env_vars(self) -> dict[str, str | None]:
        if self.case_sensitive:
            return dict(self._mapping)
        return {k.lower(): v for k, v in self._mapping.items()}


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGORA_",
        env_nested_delimiter="__",
        extra="forbid",
    )

    reflection: ReflectionConfig = Field(default_factory=ReflectionConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        mapping = _env_mapping.get()
        env_source = env_settings if mapping is None else _MappingEnvSource(settings_cls, mapping)
        sources: list[PydanticBaseSettingsSource] = [init_settings, env_source]
        yaml_path = _yaml_path.get()
        if yaml_path is not None:
            sources.append(YamlConfigSettingsSource(settings_cls, yaml_file=yaml_path))
        return tuple(sources)
