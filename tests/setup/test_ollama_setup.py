import sys
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Any

import httpx
import pytest

from ibikus.appa.agora.setup import ollama_setup as o
from ibikus.appa.agora.setup.presets import load_presets
from ibikus.appa.agora.setup.runner import CommandResult


class _Chunks(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes], fail_after: int | None = None) -> None:
        self._chunks, self._fail_after = chunks, fail_after

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for i, chunk in enumerate(self._chunks):
            if self._fail_after is not None and i >= self._fail_after:
                raise httpx.ReadError("connection reset")
            yield chunk


def _client(stream: _Chunks, length: int) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == o.INSTALLER_URL
        return httpx.Response(200, headers={"content-length": str(length)}, stream=stream)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_download_writes_file(tmp_path: Path) -> None:
    async with _client(_Chunks([b"ab", b"cd", b"ef"]), 6) as client:
        events = [e async for e in o.download_installer(client, tmp_path)]
    assert [e.done for e in events] == [2, 4, 6]
    assert events[-1].total == 6
    assert (tmp_path / "OllamaSetup.exe").read_bytes() == b"abcdef"
    assert not (tmp_path / "OllamaSetup.exe.part").exists()


async def test_download_cut_removes_part(tmp_path: Path) -> None:
    async with _client(_Chunks([b"ab", b"cd", b"ef"], fail_after=1), 6) as client:
        with pytest.raises(httpx.ReadError):
            async for _ in o.download_installer(client, tmp_path):
                pass
    assert list(tmp_path.iterdir()) == []


async def test_download_cancel_removes_part(tmp_path: Path) -> None:
    async with _client(_Chunks([b"ab", b"cd", b"ef"]), 6) as client:
        gen = o.download_installer(client, tmp_path)
        await gen.__anext__()
        await gen.aclose()  # what cancelling the consuming worker does
    assert list(tmp_path.iterdir()) == []


async def test_wait_for_server_ok_after_retries() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise httpx.ConnectError("refused")
        return httpx.Response(200, json={"version": "0.12.3"})

    sleeps: list[float] = []

    async def sleep(s: float) -> None:
        sleeps.append(s)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await o.wait_for_server(client, "http://x", sleep=sleep) is True
    assert len(sleeps) == 2


async def test_wait_for_server_timeout() -> None:
    now = [0.0]

    async def sleep(s: float) -> None:
        now[0] += s

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        ok = await o.wait_for_server(client, "http://x", clock=lambda: now[0], sleep=sleep)
    assert ok is False
    assert now[0] >= 120


def test_recommended_env_values() -> None:
    quality = next(p for p in load_presets() if p.id == "quality")
    assert o.recommended_env(quality) == {
        "OLLAMA_CONTEXT_LENGTH": "8192",
        "OLLAMA_FLASH_ATTENTION": "1",
        "OLLAMA_KV_CACHE_TYPE": "q8_0",
    }


def test_launch_installer(tmp_path: Path) -> None:
    started: list[list[str]] = []
    o.launch_installer(tmp_path / "OllamaSetup.exe", popen=lambda args: started.append(args))
    assert started == [[str(tmp_path / "OllamaSetup.exe")]]


def test_restart_calls_taskkill_then_start(tmp_path: Path) -> None:
    exe = tmp_path / "ollama.exe"
    app = tmp_path / "ollama app.exe"
    exe.write_bytes(b"")
    app.write_bytes(b"")
    calls: list[Any] = []

    def runner(args: Sequence[str], timeout_s: float) -> CommandResult:
        calls.append(("run", list(args)))
        return CommandResult(128, "", "not running")  # taskkill failing is fine

    o.restart_ollama(runner, popen=lambda args: calls.append(("start", args)), exe=exe)
    assert calls == [
        ("run", ["taskkill", "/IM", "ollama app.exe", "/F"]),
        ("run", ["taskkill", "/IM", "ollama.exe", "/F"]),
        ("start", [str(app)]),
    ]


def test_restart_without_app_uses_serve(tmp_path: Path) -> None:
    exe = tmp_path / "ollama"
    exe.write_bytes(b"")
    started: list[Any] = []
    o.restart_ollama(
        lambda a, t: CommandResult(0, "", ""), popen=lambda args: started.append(args), exe=exe
    )
    assert started == [[str(exe), "serve"]]


def test_install_hint() -> None:
    assert "install.sh" in o.install_hint("Linux")
    assert "brew install ollama" in o.install_hint("Darwin")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows registry")
def test_set_user_env_windows() -> None:
    import winreg

    from ibikus.appa.agora.setup.winenv import set_user_env

    set_user_env({"AGORA_TEST_VAR": "42"})
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
        assert winreg.QueryValueEx(key, "AGORA_TEST_VAR")[0] == "42"
        winreg.DeleteValue(key, "AGORA_TEST_VAR")


@pytest.mark.skipif(sys.platform == "win32", reason="non-Windows behaviour")
def test_set_user_env_not_windows() -> None:
    from ibikus.appa.agora.setup.winenv import set_user_env

    with pytest.raises(NotImplementedError):
        set_user_env({"A": "1"})


def test_restart_without_exe_kills_nothing() -> None:
    calls: list[Any] = []
    with pytest.raises(FileNotFoundError):
        o.restart_ollama(lambda a, t: calls.append(a) or CommandResult(0, "", ""), exe=None)
    assert calls == []


def test_spawn_detached_hides_output(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    seen: dict[str, Any] = {}

    def fake_popen(args: list[str], **kwargs: Any) -> None:
        seen.update(kwargs)

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    o.spawn_detached(["ollama", "serve"])
    assert seen["stdin"] is subprocess.DEVNULL
    assert seen["stdout"] is subprocess.DEVNULL
    assert seen["stderr"] is subprocess.DEVNULL
    if sys.platform == "win32":
        assert seen["creationflags"]
    else:
        assert seen["start_new_session"] is True
