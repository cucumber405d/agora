"""Setup wizard tests with fake diagnostics, HTTP, processes and environment."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import yaml
from textual.pilot import Pilot
from textual.widgets import Button

from ibikus.appa.agora.config import AppConfig
from ibikus.appa.agora.setup.diagnostics import Check, Gpu, OllamaInfo, SystemReport
from ibikus.appa.agora.setup.ollama_setup import INSTALLER_URL
from ibikus.appa.agora.setup.runner import CommandResult
from ibikus.appa.agora.tui.app import AgoraApp
from ibikus.appa.agora.tui.dialogs import HelpScreen
from ibikus.appa.agora.tui.setup_wizard import SetupDeps, SetupWizard

from .helpers import factory, make_project, wait_group

PS = (
    "NAME          ID     SIZE    PROCESSOR    CONTEXT    UNTIL\n"
    "qwen3.5:9b    abc    8 GB    100% GPU     8192       4 minutes\n"
)


@dataclass
class World:
    """Mutable fake machine shared by the fakes."""

    ram: float = 32
    gpu: Gpu | None = field(default_factory=lambda: Gpu("RTX 4070", 12))
    free_disk: float = 100
    installed: bool = True
    running: bool = True
    models: list[str] = field(default_factory=list)
    pulled: list[str] = field(default_factory=list)
    started: list[list[str]] = field(default_factory=list)
    env_written: list[dict[str, str]] = field(default_factory=list)
    installer_fails: bool = False
    installer_slow: bool = False
    server_after_install: bool = True

    async def collect(self) -> SystemReport:
        ollama = OllamaInfo(
            self.installed, self.running, "0.12.3" if self.running else None, tuple(self.models)
        )
        status = "ok" if self.running else "error"
        checks = (Check("OS", "ok", "Windows 11"), Check("Ollama", status, "state"))  # type: ignore[arg-type]
        return SystemReport("Windows 11", self.ram, self.free_disk, self.gpu, ollama, checks)

    def handler(self, request: httpx.Request) -> httpx.Response:
        if str(request.url) == INSTALLER_URL:
            if self.installer_fails:
                raise httpx.ConnectError("no internet")
            return httpx.Response(200, headers={"content-length": "4"}, content=b"exe!")
        path = request.url.path
        if path == "/api/version":
            if not self.running:
                raise httpx.ConnectError("refused")
            return httpx.Response(200, json={"version": "0.12.3"})
        if path == "/api/pull":
            model = json.loads(request.content)["model"]
            self.pulled.append(model)
            self.models.append(model)
            lines = [{"status": "downloading", "total": 10, "completed": 10}, {"status": "success"}]
            return httpx.Response(
                200, content=b"".join(json.dumps(x).encode() + b"\n" for x in lines)
            )
        if path == "/api/generate":
            return httpx.Response(200, json={"response": "ok", "done": True})
        return httpx.Response(404)

    def popen(self, args: list[str]) -> None:
        self.started.append(args)
        if args[0].endswith("OllamaSetup.exe") and self.server_after_install:
            self.installed = self.running = True

    def runner(self, args: Sequence[str], timeout_s: float) -> CommandResult:
        if list(args)[-1] == "ps":
            return CommandResult(0, PS, "")
        return CommandResult(0, "", "")

    def deps(self, tmp_path: Path) -> SetupDeps:
        async def wait_server(client: httpx.AsyncClient, base_url: str) -> bool:
            return self.running

        return SetupDeps(
            collect=self.collect,
            client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(self.handler)),
            runner=self.runner,
            popen=self.popen,
            set_env=self.env_written.append,
            environ={},
            config_path=tmp_path / "home" / "config.yaml",
            downloads=tmp_path / "downloads",
            platform="win32",
            os_name="Windows",
            wait_server=wait_server,
            ollama_exe=tmp_path / "ollama.exe",
        )


def _app(tmp_path: Path, world: World, start_wizard: bool = True) -> AgoraApp:
    return AgoraApp(
        AppConfig(),
        root=make_project(tmp_path),
        service_factory=factory(),
        start_wizard=start_wizard,
        setup_deps=world.deps(tmp_path),
    )


async def settle(pilot: Pilot[Any]) -> None:
    await pilot.pause()
    await wait_group(pilot.app, "setup")
    await pilot.pause()


async def press(pilot: Pilot[Any], button: str) -> None:
    btn = pilot.app.screen.query_one(f"#{button}", Button)
    assert btn.display and not btn.disabled, f"#{button} is not available"
    btn.press()
    await settle(pilot)


def wizard(pilot: Pilot[Any]) -> SetupWizard:
    assert isinstance(pilot.app.screen, SetupWizard)
    return pilot.app.screen


async def test_first_run_opens_wizard(tmp_path: Path) -> None:
    async with _app(tmp_path, World()).run_test(size=(110, 36)) as pilot:
        await settle(pilot)
        assert wizard(pilot).step == 0
        assert "Windows 11" in wizard(pilot).body_text


async def test_wizard_happy_path(tmp_path: Path) -> None:
    world = World()
    app = _app(tmp_path, world)
    async with app.run_test(size=(110, 36)) as pilot:
        await settle(pilot)
        await press(pilot, "next")  # -> configuration
        assert wizard(pilot).choice is not None and wizard(pilot).choice.id == "quality"
        await press(pilot, "next")  # -> ollama (running)
        await press(pilot, "next")  # -> settings
        await press(pilot, "action")  # apply recommended
        assert world.env_written[0]["OLLAMA_CONTEXT_LENGTH"] == "8192"
        await press(pilot, "next")  # -> models
        await press(pilot, "action")  # download
        assert world.pulled == ["qwen3.5:9b", "qwen3:14b"]
        await press(pilot, "next")  # -> done (writes config)
        assert "Processor" in wizard(pilot).body_text
        await press(pilot, "next")  # finish
        assert not isinstance(app.screen, SetupWizard)
        data = yaml.safe_load((tmp_path / "home" / "config.yaml").read_text(encoding="utf-8"))
        assert data["reflection"]["critic"]["name"] == "qwen3:14b"
        assert app.config.reflection.generator.name == "qwen3.5:9b"


async def test_wizard_skip_everything_still_writes_config(tmp_path: Path) -> None:
    world = World(running=False, installed=False, gpu=None, ram=16)
    async with _app(tmp_path, world).run_test(size=(110, 36)) as pilot:
        await settle(pilot)
        await press(pilot, "next")
        assert wizard(pilot).choice.id == "light"  # type: ignore[union-attr]
        await press(pilot, "next")  # ollama
        await press(pilot, "skip")  # settings
        await press(pilot, "skip")  # models
        await press(pilot, "skip")  # done
        await press(pilot, "next")  # finish
    assert (tmp_path / "home" / "config.yaml").is_file()
    assert world.pulled == []


async def test_wizard_installs_ollama(tmp_path: Path) -> None:
    world = World(running=False, installed=False)
    async with _app(tmp_path, world).run_test(size=(110, 36)) as pilot:
        await settle(pilot)
        await press(pilot, "next")
        await press(pilot, "next")  # ollama step
        assert "Download and run installer" in str(
            pilot.app.screen.query_one("#action", Button).label
        )
        await press(pilot, "action")
        assert world.started == [[str(tmp_path / "downloads" / "OllamaSetup.exe")]]
        assert "running" in wizard(pilot).body_text


async def test_wizard_network_error_then_retry(tmp_path: Path) -> None:
    world = World(running=False, installed=False, installer_fails=True)
    async with _app(tmp_path, world).run_test(size=(110, 36)) as pilot:
        await settle(pilot)
        await press(pilot, "next")
        await press(pilot, "next")
        await press(pilot, "action")
        assert "no internet" in wizard(pilot).status_text
        assert str(pilot.app.screen.query_one("#action", Button).label) == "Retry"
        world.installer_fails = False
        await press(pilot, "action")
        assert world.started
        assert wizard(pilot).status_text == "" or "no internet" not in wizard(pilot).status_text


async def test_wizard_cancel_download_cleans_up(tmp_path: Path) -> None:
    world = World(running=False, installed=False)
    gate = asyncio.Event()
    async with _app(tmp_path, world).run_test(size=(110, 36)) as pilot:
        await settle(pilot)
        await press(pilot, "next")
        await press(pilot, "next")
        original = world.handler

        def slow(request: httpx.Request) -> httpx.Response:
            if str(request.url) == INSTALLER_URL:

                class Stream(httpx.AsyncByteStream):
                    async def __aiter__(self):  # type: ignore[no-untyped-def]
                        yield b"ex"
                        await gate.wait()
                        yield b"e!"

                return httpx.Response(200, headers={"content-length": "4"}, stream=Stream())
            return original(request)

        world.handler = slow  # type: ignore[method-assign]
        pilot.app.screen.query_one("#action", Button).press()
        for _ in range(20):
            await pilot.pause(0.02)
            if (tmp_path / "downloads" / "OllamaSetup.exe.part").exists():
                break
        await pilot.press("escape")
        await settle(pilot)
        assert isinstance(pilot.app.screen, SetupWizard)  # Esc cancelled the download only
        assert wizard(pilot).step == 2
        assert list((tmp_path / "downloads").iterdir()) == []
        assert world.started == []


async def test_wizard_disk_warning(tmp_path: Path) -> None:
    world = World(free_disk=5)
    async with _app(tmp_path, world).run_test(size=(110, 36)) as pilot:
        await settle(pilot)
        await press(pilot, "next")
        assert "Not enough disk space" in wizard(pilot).status_text


async def test_wizard_esc_closes_without_writing(tmp_path: Path) -> None:
    async with _app(tmp_path, World()).run_test(size=(110, 36)) as pilot:
        await settle(pilot)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(pilot.app.screen, SetupWizard)
    assert not (tmp_path / "home" / "config.yaml").exists()


async def test_wizard_keyboard_only(tmp_path: Path) -> None:
    async with _app(tmp_path, World()).run_test(size=(110, 36)) as pilot:
        await settle(pilot)
        assert pilot.app.focused is not None and pilot.app.focused.id == "next"
        await pilot.press("enter")
        await settle(pilot)
        assert wizard(pilot).step == 1


async def test_f8_opens_wizard(tmp_path: Path) -> None:
    async with _app(tmp_path, World(), start_wizard=False).run_test(size=(110, 36)) as pilot:
        await pilot.pause()
        assert not isinstance(pilot.app.screen, SetupWizard)
        await pilot.press("f8")
        await settle(pilot)
        assert isinstance(pilot.app.screen, SetupWizard)


async def test_f8_blocked_during_run(tmp_path: Path) -> None:
    app = _app(tmp_path, World(), start_wizard=False)
    async with app.run_test(size=(110, 36)) as pilot:
        await pilot.pause()
        app.run_in_progress = True
        await pilot.press("f8")
        await pilot.pause()
        assert not isinstance(app.screen, SetupWizard)


async def test_help_shows_version(tmp_path: Path) -> None:
    from ibikus.appa.agora import __version__

    async with _app(tmp_path, World(), start_wizard=False).run_test(size=(110, 36)) as pilot:
        await pilot.pause()
        await pilot.press("f1")
        await pilot.pause()
        assert isinstance(pilot.app.screen, HelpScreen)
        assert f"Agora {__version__}" in pilot.app.screen.about_text
        assert "github.com/cucumber405d/agora" in pilot.app.screen.about_text
