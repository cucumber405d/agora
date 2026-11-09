import pytest
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openrouter import OpenRouterModel

from ibikus.appa.agora.config import ConfigError, ModelConfig
from ibikus.appa.agora.llm.factory import build_model, build_settings, describe, required_env_key


def test_ollama_model_uses_base_url() -> None:
    m = build_model(
        ModelConfig(
            provider="ollama", name="qwen2.5:7b", temperature=0.9, base_url="http://h:1/v1"
        ),
        env={},
    )
    assert isinstance(m, OllamaModel)
    assert m.model_name == "qwen2.5:7b"
    assert str(m.client.base_url).startswith("http://h:1/v1")


def test_ollama_default_base_url() -> None:
    m = build_model(ModelConfig(provider="ollama", name="x", temperature=0.9), env={})
    assert isinstance(m, OllamaModel)
    assert str(m.client.base_url).startswith("http://localhost:11434/v1")


@pytest.mark.parametrize(
    ("provider", "cls", "key"),
    [
        ("anthropic", AnthropicModel, "ANTHROPIC_API_KEY"),
        ("openai", OpenAIChatModel, "OPENAI_API_KEY"),
        ("openrouter", OpenRouterModel, "OPENROUTER_API_KEY"),
    ],
)
def test_cloud_models(provider: str, cls: type, key: str) -> None:
    cfg = ModelConfig.model_validate({"provider": provider, "name": "vendor/m", "temperature": 0.1})
    assert isinstance(build_model(cfg, env={key: "k"}), cls)
    assert required_env_key(cfg.provider) == key


def test_ollama_needs_no_key() -> None:
    assert required_env_key("ollama") is None


def test_missing_key_raises_config_error() -> None:
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY is not set"):
        build_model(ModelConfig(provider="anthropic", name="m", temperature=0.1), env={})


def test_settings() -> None:
    s = build_settings(ModelConfig(provider="ollama", name="x", temperature=0.9))
    assert s.get("temperature") == 0.9
    assert s.get("max_retries") == 3
    assert s.get("timeout") == 60
    assert "max_tokens" not in s


def test_settings_max_tokens_when_set() -> None:
    s = build_settings(ModelConfig(provider="ollama", name="x", temperature=0.9, max_tokens=500))
    assert s.get("max_tokens") == 500


def test_describe() -> None:
    cfg = ModelConfig(provider="ollama", name="qwen2.5:7b", temperature=0.9)
    assert describe(cfg) == "ollama/qwen2.5:7b t=0.9"


def test_invalid_model_name_becomes_config_error() -> None:
    cfg = ModelConfig(provider="openrouter", name="no-prefix", temperature=0.1)
    with pytest.raises(ConfigError, match="no-prefix"):
        build_model(cfg, env={"OPENROUTER_API_KEY": "k"})
