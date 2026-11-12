"""Generate ~/.agora/config.yaml from a preset, keeping the user's other settings."""

from __future__ import annotations

import copy
import logging
import os
import shutil
from pathlib import Path
from typing import Any

import yaml

from .presets import Preset

logger = logging.getLogger(__name__)

OLLAMA_V1_URL = "http://localhost:11434/v1"
GENERATOR_TEMPERATURE = 0.9
CRITIC_TEMPERATURE = 0.1


def _model(name: str, temperature: float) -> dict[str, Any]:
    return {
        "provider": "ollama",
        "name": name,
        "temperature": temperature,
        "base_url": OLLAMA_V1_URL,
        "think": False,
    }


def build_config_data(preset: Preset, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    """The existing config with the preset's models, language and context budget applied."""
    data = copy.deepcopy(existing) if existing else {}
    reflection = data.setdefault("reflection", {})
    reflection["generator"] = _model(preset.generator, GENERATOR_TEMPERATURE)
    reflection["critic"] = _model(preset.critic, CRITIC_TEMPERATURE)
    reflection["language"] = "auto"
    data.setdefault("context", {})["max_total_tokens"] = preset.max_total_tokens
    return data


def read_existing(path: Path) -> dict[str, Any] | None:
    """The YAML mapping at `path`, or None if it is missing or unreadable."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        if path.exists():
            logger.warning("Ignoring unreadable config %s", path, exc_info=True)
        return None
    return data if isinstance(data, dict) else None


def write_config(data: dict[str, Any], path: Path) -> Path | None:
    """Write atomically (temp file + rename). Returns the .bak path if a file was replaced."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        "# Written by the Agora setup wizard.\n"
        + yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    bak: Path | None = None
    try:
        if path.exists():
            bak = path.with_name(path.name + ".bak")
            shutil.copy2(path, bak)
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
    return bak
