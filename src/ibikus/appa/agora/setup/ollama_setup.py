"""Install, configure and restart Ollama on behalf of the user."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .presets import Preset
from .runner import Runner

logger = logging.getLogger(__name__)

INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"
INSTALLER_NAME = "OllamaSetup.exe"
SERVER_TIMEOUT_S = 120

Popen = Callable[[list[str]], Any]


def _popen(args: list[str]) -> Any:
    return subprocess.Popen(args)  # detached enough: we never wait for it


@dataclass(frozen=True)
class DownloadProgress:
    done: int
    total: int | None


async def download_installer(
    client: httpx.AsyncClient, dest_dir: Path
) -> AsyncIterator[DownloadProgress]:
    """Download OllamaSetup.exe into dest_dir via a .part file; a failed or cancelled
    download leaves nothing behind."""
    dest_dir.mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240 - instant local op
    final = dest_dir / INSTALLER_NAME
    part = dest_dir / (INSTALLER_NAME + ".part")
    try:
        async with client.stream("GET", INSTALLER_URL, follow_redirects=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers["content-length"]) if "content-length" in r.headers else None
            done = 0
            with part.open("wb") as fh:
                async for chunk in r.aiter_bytes():
                    fh.write(chunk)
                    done += len(chunk)
                    yield DownloadProgress(done, total)
        part.replace(final)
    finally:
        part.unlink(missing_ok=True)


def launch_installer(path: Path, popen: Popen = _popen) -> None:
    """Start the installer; the user goes through it themselves."""
    popen([str(path)])


async def wait_for_server(
    client: httpx.AsyncClient,
    base_url: str,
    timeout_s: float = SERVER_TIMEOUT_S,
    interval_s: float = 2,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> bool:
    """Poll /api/version until Ollama answers or timeout_s passes."""
    deadline = clock() + timeout_s
    while True:
        try:
            r = await client.get(f"{base_url}/api/version", timeout=3)
            if r.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        if clock() >= deadline:
            return False
        await sleep(interval_s)


def recommended_env(preset: Preset) -> dict[str, str]:
    return {
        "OLLAMA_CONTEXT_LENGTH": str(preset.ollama_context),
        "OLLAMA_FLASH_ATTENTION": "1",
        "OLLAMA_KV_CACHE_TYPE": "q8_0",
    }


def restart_ollama(runner: Runner, popen: Popen = _popen, exe: Path | None = None) -> None:
    """Stop the user's Ollama (tray app and server) and start it again so new environment
    variables take effect. Also used to start an installed but stopped Ollama."""
    for image in ("ollama app.exe", "ollama.exe"):
        res = runner(["taskkill", "/IM", image, "/F"], 10)
        logger.info("taskkill %s -> %s", image, res.returncode)
    if exe is None:
        raise FileNotFoundError("Ollama executable not found")
    tray = exe.with_name("ollama app.exe")
    popen([str(tray)] if tray.is_file() else [str(exe), "serve"])


def install_hint(os_name: str) -> str:
    if os_name == "Darwin":
        return (
            "Install Ollama: `brew install ollama` or download it from https://ollama.com/download"
        )
    return "Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`"
