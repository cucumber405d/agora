"""Collect what the setup wizard needs to know about this machine and its Ollama."""

from __future__ import annotations

import logging
import os
import platform as _platform
import re
import shutil
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import httpx
import psutil

from .runner import Runner, run_command

logger = logging.getLogger(__name__)

Status = Literal["ok", "warn", "error"]
_RANK: dict[Status, int] = {"ok": 0, "warn": 1, "error": 2}
GB = 1024**3
OLLAMA_ENV_KEYS = ("OLLAMA_CONTEXT_LENGTH", "OLLAMA_FLASH_ATTENTION", "OLLAMA_KV_CACHE_TYPE")
DEFAULT_OLLAMA_URL = "http://localhost:11434"
MIN_RAM_GB = 8


@dataclass(frozen=True)
class Check:
    name: str
    status: Status
    detail: str


@dataclass(frozen=True)
class Gpu:
    name: str
    vram_gb: float | None  # None: the size could not be determined reliably


@dataclass(frozen=True)
class OllamaInfo:
    installed: bool
    running: bool
    version: str | None = None
    models: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LoadedModel:
    name: str
    processor: str
    context: int | None


@dataclass(frozen=True)
class SystemReport:
    os: str
    ram_gb: float
    free_disk_gb: float
    gpu: Gpu | None
    ollama: OllamaInfo
    checks: tuple[Check, ...]

    @property
    def worst(self) -> Status:
        return max((c.status for c in self.checks), key=_RANK.__getitem__, default="ok")


def parse_nvidia_smi(text: str) -> Gpu | None:
    """Parse `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits`;
    with several GPUs the one with the most memory wins."""
    best: Gpu | None = None
    for line in text.splitlines():
        name, sep, mib = line.rpartition(",")
        if not sep:
            continue
        try:
            vram = float(mib.strip()) / 1024
        except ValueError:
            continue
        if best is None or (best.vram_gb or 0) < vram:
            best = Gpu(name.strip(), vram)
    return best


def parse_ollama_ps(text: str) -> list[LoadedModel]:
    """Parse the table printed by `ollama ps` (cells are separated by 2+ spaces)."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    header = re.split(r"\s{2,}", lines[0].strip())
    out = []
    for line in lines[1:]:
        row = dict(zip(header, re.split(r"\s{2,}", line.strip()), strict=False))
        raw = row.get("CONTEXT", "").split()
        context = int(raw[0]) if raw and raw[0].isdigit() else None
        out.append(LoadedModel(row.get("NAME", ""), row.get("PROCESSOR", ""), context))
    return out


def ollama_models_dir(env: Mapping[str, str]) -> Path:
    value = env.get("OLLAMA_MODELS")
    return Path(value).expanduser() if value else Path("~/.ollama/models").expanduser()


def find_ollama_exe(
    env: Mapping[str, str], which: Callable[[str], str | None] = shutil.which
) -> Path | None:
    found = which("ollama")
    if found:
        return Path(found)
    local = env.get("LOCALAPPDATA")
    if local:
        candidate = Path(local) / "Programs" / "Ollama" / "ollama.exe"
        if candidate.is_file():
            return candidate
    return None


def _existing(path: Path) -> Path:
    while not path.exists() and path.parent != path:
        path = path.parent
    return path


def _ram() -> tuple[float, Check]:
    total = psutil.virtual_memory().total / GB
    status: Status = "ok" if total >= MIN_RAM_GB else "warn"
    return total, Check("RAM", status, f"{total:.1f} GB")


def _disk(env: Mapping[str, str]) -> tuple[float, Check]:
    target = ollama_models_dir(env)
    free = shutil.disk_usage(_existing(target)).free / GB
    return free, Check("Disk", "ok", f"{free:.1f} GB free for models ({target})")


def _gpu(runner: Runner, platform: str) -> tuple[Gpu | None, Check]:
    res = runner(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], 10
    )
    if res.returncode == 0 and (gpu := parse_nvidia_smi(res.stdout)) is not None:
        return gpu, Check("GPU", "ok", f"{gpu.name}, {gpu.vram_gb:.1f} GB VRAM")
    if platform == "win32":
        ps = runner(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_VideoController).Name",
            ],
            10,
        )
        names = (
            [n.strip() for n in ps.stdout.splitlines() if n.strip()] if ps.returncode == 0 else []
        )
        if names:
            return Gpu(names[0], None), Check(
                "GPU", "warn", f"{names[0]}, VRAM unknown (only NVIDIA GPUs are measured)"
            )
    detail = "no NVIDIA GPU found" + (f" ({res.stderr.strip()})" if res.stderr.strip() else "")
    return None, Check("GPU", "warn", detail + "; models will run on the CPU")


async def _ollama(
    client: httpx.AsyncClient, base_url: str, env: Mapping[str, str], network: bool
) -> tuple[OllamaInfo, Check]:
    installed = find_ollama_exe(env) is not None
    ollama_env = {k: env[k] for k in OLLAMA_ENV_KEYS if k in env}
    if not network:
        info = OllamaInfo(installed, False, env=ollama_env)
        state = "installed" if installed else "not found"
        return info, Check("Ollama", "warn", f"{state}; server not checked (no network)")
    try:
        version = (await client.get(f"{base_url}/api/version", timeout=3)).json()["version"]
        tags = (await client.get(f"{base_url}/api/tags", timeout=3)).json().get("models", [])
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.info("Ollama not reachable at %s: %s", base_url, e)
        info = OllamaInfo(installed, False, env=ollama_env)
        if installed:
            return info, Check("Ollama", "error", "installed but not running")
        return info, Check("Ollama", "error", "not installed")
    models = tuple(str(m["name"]) for m in tags)
    info = OllamaInfo(True, True, str(version), models, ollama_env)
    return info, Check("Ollama", "ok", f"{version} running, {len(models)} models")


async def collect(
    *,
    base_url: str = DEFAULT_OLLAMA_URL,
    runner: Runner = run_command,
    client: httpx.AsyncClient | None = None,
    env: Mapping[str, str] | None = None,
    network: bool = True,
    platform: str = sys.platform,
) -> SystemReport:
    """Run every check independently: one failing check never hides the others."""
    env = dict(os.environ if env is None else env)
    checks: list[Check] = [Check("OS", "ok", f"{_platform.system()} {_platform.release()}")]
    ram = free = 0.0
    gpu: Gpu | None = None
    try:
        ram, check = _ram()
    except Exception as e:
        check = Check("RAM", "warn", f"unknown ({e})")
    checks.append(check)
    try:
        free, check = _disk(env)
    except Exception as e:
        check = Check("Disk", "warn", f"unknown ({e})")
    checks.append(check)
    try:
        gpu, check = _gpu(runner, platform)
    except Exception as e:
        check = Check("GPU", "warn", f"unknown ({e})")
    checks.append(check)
    own = client is None
    http = client or httpx.AsyncClient()
    try:
        ollama, check = await _ollama(http, base_url, env, network)
    except Exception as e:
        ollama, check = OllamaInfo(False, False), Check("Ollama", "warn", f"unknown ({e})")
    finally:
        if own:
            await http.aclose()
    checks.append(check)
    os_name = f"{_platform.system()} {_platform.release()}"
    return SystemReport(os_name, ram, free, gpu, ollama, tuple(checks))
