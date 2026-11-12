"""Per-user locations: ~/.agora (or AGORA_HOME) holds config, logs and downloads."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path


def _real_default_home() -> Path:
    return Path("~/.agora").expanduser()


def _default_home() -> Path:
    # Indirection so tests can redirect the default home without touching env vars.
    return _real_default_home()


def agora_home(env: Mapping[str, str] | None = None) -> Path:
    """AGORA_HOME if set, otherwise ~/.agora."""
    env = os.environ if env is None else env
    value = env.get("AGORA_HOME")
    return Path(value).expanduser() if value else _default_home()


def user_config_path(env: Mapping[str, str] | None = None) -> Path:
    return agora_home(env) / "config.yaml"


def downloads_dir(env: Mapping[str, str] | None = None) -> Path:
    return agora_home(env) / "downloads"


def is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))
