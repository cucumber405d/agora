from pathlib import Path

import pytest

from ibikus.appa.agora.config.loader import ConfigError, load_config


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_when_no_file(tmp_path: Path) -> None:
    cfg = load_config(env={}, cwd=tmp_path)
    assert cfg.reflection.max_iterations == 3
    assert cfg.reflection.approve_threshold == 8
    gen = cfg.reflection.generator
    assert (gen.provider, gen.name) == ("ollama", "qwen2.5:7b")
    assert gen.temperature == 0.9
    assert gen.base_url == "http://localhost:11434/v1"
    assert cfg.reflection.critic.provider == "anthropic"
    assert cfg.reflection.critic.name == "claude-haiku-4-5"
    assert cfg.reflection.critic.temperature == 0.1
    assert cfg.context.max_file_kb == 256
    assert cfg.context.max_total_tokens == 32000
    assert cfg.context.allowed_ext == [".md", ".txt", ".py", ".java", ".yaml", ".json"]
    assert cfg.observability.langfuse.enabled == "auto"


def test_explicit_path_wins_over_agora_config_env_and_cwd(tmp_path: Path) -> None:
    _write(tmp_path / "config" / "agora.yaml", "reflection:\n  max_iterations: 4\n")
    env_file = _write(tmp_path / "env.yaml", "reflection:\n  max_iterations: 5\n")
    explicit = _write(tmp_path / "explicit.yaml", "reflection:\n  max_iterations: 6\n")
    env = {"AGORA_CONFIG": str(env_file)}
    assert load_config(explicit, env=env, cwd=tmp_path).reflection.max_iterations == 6
    assert load_config(env=env, cwd=tmp_path).reflection.max_iterations == 5
    assert load_config(env={}, cwd=tmp_path).reflection.max_iterations == 4


def test_env_overrides_yaml(tmp_path: Path) -> None:
    p = _write(tmp_path / "a.yaml", "reflection:\n  critic:\n    temperature: 0.3\n")
    cfg = load_config(p, env={"AGORA_REFLECTION__CRITIC__TEMPERATURE": "0.2"})
    assert cfg.reflection.critic.temperature == 0.2
    # other critic fields keep their defaults
    assert cfg.reflection.critic.provider == "anthropic"


def test_api_key_in_yaml_is_rejected(tmp_path: Path) -> None:
    p = _write(tmp_path / "a.yaml", 'reflection:\n  critic:\n    api_key: "x"\n')
    with pytest.raises(ConfigError, match=r"reflection\.critic\.api_key"):
        load_config(p, env={})


def test_invalid_value_names_field(tmp_path: Path) -> None:
    p = _write(tmp_path / "a.yaml", "reflection:\n  approve_threshold: 11\n")
    with pytest.raises(ConfigError, match=r"reflection\.approve_threshold"):
        load_config(p, env={})


def test_missing_explicit_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml", env={})


def test_repo_config_file_is_valid() -> None:
    repo_cfg = Path(__file__).resolve().parents[2] / "config" / "agora.yaml"
    cfg = load_config(repo_cfg, env={})
    assert cfg.reflection.max_iterations == 3


def test_partial_yaml_model_override_keeps_role_defaults(tmp_path: Path) -> None:
    p = _write(tmp_path / "a.yaml", "reflection:\n  generator:\n    temperature: 1.2\n")
    gen = load_config(p, env={}).reflection.generator
    assert (gen.provider, gen.name, gen.temperature) == ("ollama", "qwen2.5:7b", 1.2)
    assert gen.base_url == "http://localhost:11434/v1"


def test_yaml_provider_switch_drops_role_defaults(tmp_path: Path) -> None:
    p = _write(
        tmp_path / "a.yaml",
        "reflection:\n  generator: {provider: openai, name: gpt-4o-mini, temperature: 0.7}\n",
    )
    gen = load_config(p, env={}).reflection.generator
    assert (gen.provider, gen.name, gen.base_url) == ("openai", "gpt-4o-mini", None)


def test_env_provider_switch_drops_role_defaults(tmp_path: Path) -> None:
    env = {
        "AGORA_REFLECTION__GENERATOR__PROVIDER": "openai",
        "AGORA_REFLECTION__GENERATOR__NAME": "gpt-4o-mini",
        "AGORA_REFLECTION__GENERATOR__TEMPERATURE": "0.7",
    }
    assert load_config(env=env, cwd=tmp_path).reflection.generator.base_url is None


def test_provider_switch_requires_name(tmp_path: Path) -> None:
    p = _write(tmp_path / "a.yaml", "reflection:\n  critic: {provider: ollama, temperature: 0.1}\n")
    with pytest.raises(ConfigError, match=r"reflection\.critic\.name"):
        load_config(p, env={})


def test_language_default_auto(tmp_path: Path) -> None:
    assert load_config(env={}, cwd=tmp_path).reflection.language == "auto"
