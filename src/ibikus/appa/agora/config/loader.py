"""Layered configuration loading: env > YAML file > built-in defaults."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import ValidationError

from ibikus.appa.agora.paths import user_config_path

from .models import AppConfig, _env_mapping, _yaml_path


class ConfigError(Exception):
    """Invalid or missing configuration. str() lists one '<field>: <msg>' per line."""


def find_config_path(path: Path | None, env: Mapping[str, str], cwd: Path) -> Path | None:
    """First existing config: explicit path, AGORA_CONFIG, ./config/agora.yaml,
    ~/.agora/config.yaml. None means built-in defaults (first run)."""
    if path is not None:
        if not path.is_file():
            raise ConfigError(f"Config file not found: {path}")
        return path
    from_env = env.get("AGORA_CONFIG")
    if from_env:
        p = Path(from_env)
        if not p.is_file():
            raise ConfigError(f"Config file not found (AGORA_CONFIG): {p}")
        return p
    local = cwd / "config" / "agora.yaml"
    if local.is_file():
        return local
    user = user_config_path(env)
    return user if user.is_file() else None


def _format(err: ValidationError) -> str:
    lines = []
    for e in err.errors():
        loc = ".".join(str(part) for part in e["loc"])
        lines.append(f"{loc}: {e['msg']}")
    return "\n".join(lines)


def load_config(
    path: Path | None = None,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
) -> AppConfig:
    """Build AppConfig. Precedence: AGORA_* env > YAML (see find_config_path) > defaults."""
    env_map = dict(os.environ if env is None else env)
    yaml_file = find_config_path(path, env_map, cwd or Path.cwd())
    yaml_token = _yaml_path.set(yaml_file)
    env_token = _env_mapping.set({k: v for k, v in env_map.items() if k != "AGORA_CONFIG"})
    try:
        return AppConfig()
    except ValidationError as e:
        raise ConfigError(_format(e)) from e
    finally:
        _yaml_path.reset(yaml_token)
        _env_mapping.reset(env_token)
