"""First-run setup wizard: diagnostics, configuration, Ollama, its settings, models."""

from __future__ import annotations

import logging
import os
import platform as _platform
import sys
from collections.abc import Awaitable, Callable, Mapping, MutableMapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import httpx
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, OptionList, ProgressBar, Static
from textual.widgets.option_list import Option

from ibikus.appa.agora.paths import downloads_dir, user_config_path
from ibikus.appa.agora.setup.config_writer import build_config_data, read_existing, write_config
from ibikus.appa.agora.setup.diagnostics import (
    DEFAULT_OLLAMA_URL,
    Check,
    SystemReport,
    collect,
    find_ollama_exe,
)
from ibikus.appa.agora.setup.models import PullError, missing_models, pull, verify
from ibikus.appa.agora.setup.ollama_setup import (
    Popen,
    download_installer,
    install_hint,
    launch_installer,
    recommended_env,
    restart_ollama,
    wait_for_server,
)
from ibikus.appa.agora.setup.presets import (
    Preset,
    default_choice,
    disk_shortfall_gb,
    load_presets,
    recommend,
    unmet,
)
from ibikus.appa.agora.setup.runner import Runner, run_command

logger = logging.getLogger(__name__)

STEPS = ("System", "Configuration", "Ollama", "Ollama settings", "Models", "Done")
SYSTEM, CONFIGURATION, OLLAMA, SETTINGS, MODELS, DONE = range(len(STEPS))
_MARK = {"ok": ("✓", "green"), "warn": ("⚠", "yellow"), "error": ("✕", "red")}
_BUTTONS = ("back", "action", "skip", "next")


def _set_env_default() -> Callable[[Mapping[str, str]], None] | None:
    if sys.platform != "win32":
        return None
    from ibikus.appa.agora.setup.winenv import set_user_env

    return set_user_env


def _popen_default(args: list[str]) -> object:
    import subprocess

    return subprocess.Popen(args)


@dataclass
class SetupDeps:
    """Everything the wizard touches outside the process; tests pass fakes."""

    collect: Callable[[], Awaitable[SystemReport]]
    client_factory: Callable[[], httpx.AsyncClient]
    runner: Runner
    popen: Popen
    set_env: Callable[[Mapping[str, str]], None] | None
    environ: MutableMapping[str, str]
    config_path: Path
    downloads: Path
    base_url: str = DEFAULT_OLLAMA_URL
    platform: str = sys.platform
    os_name: str = field(default_factory=_platform.system)
    wait_server: Callable[[httpx.AsyncClient, str], Awaitable[bool]] = wait_for_server
    ollama_exe: Path | None = None


def default_deps() -> SetupDeps:
    return SetupDeps(
        collect=collect,
        client_factory=httpx.AsyncClient,
        runner=run_command,
        popen=_popen_default,
        set_env=_set_env_default(),
        environ=os.environ,
        config_path=user_config_path(),
        downloads=downloads_dir(),
        ollama_exe=find_ollama_exe(os.environ),
    )


def _checks_text(checks: tuple[Check, ...] | list[Check]) -> Text:
    text = Text()
    for c in checks:
        mark, style = _MARK[c.status]
        text.append(f" {mark} ", style=f"bold {style}")
        text.append(f"{c.name}: ", style="bold")
        text.append(c.detail + "\n")
    return text


class SetupWizard(ModalScreen[Path | None]):
    """Dismisses with the path of the written config, or None when closed with Esc."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "escape", "Close"),
        Binding("left", "move(-1)", show=False),
        Binding("right", "move(1)", show=False),
    ]

    def __init__(self, deps: SetupDeps, shadowed_by: Path | None = None) -> None:
        super().__init__()
        self.deps = deps
        self.shadowed_by = shadowed_by  # a config file that wins over ours at startup
        self.presets = load_presets()
        self.step = SYSTEM
        self.report: SystemReport | None = None
        self.choice: Preset | None = None
        self.written: Path | None = None
        self.body_text = ""
        self.status_text = ""
        self._action: Callable[[], Any] | None = None

    # -- layout -----------------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard", classes="dialog"):
            yield Static("", id="wizard-steps")
            yield Static("", id="wizard-body")
            yield OptionList(id="wizard-presets")
            yield ProgressBar(total=100, show_eta=False, id="wizard-bar")
            yield Static("", id="wizard-status")
            with Horizontal(id="wizard-buttons"):
                yield Button("Back", id="back")
                yield Button("", id="action")
                yield Button("Skip", id="skip")
                yield Button("Next", id="next", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#wizard").border_title = "Agora setup"
        self._show()
        self._diagnose()

    # -- rendering ----------------------------------------------------------------------------

    def _body(self, text: Text | str) -> None:
        text = Text(text) if isinstance(text, str) else text
        self.body_text = text.plain
        self.query_one("#wizard-body", Static).update(text)

    def _status(self, message: str, error: bool = False) -> None:
        self.status_text = message
        self.query_one("#wizard-status", Static).update(
            Text(message, style="bold #ff5555" if error else "#ffff00")
        )

    def _buttons(
        self, action: str | None = None, run: Callable[[], Any] | None = None, skip: bool = False
    ) -> None:
        btn = self.query_one("#action", Button)
        btn.display = action is not None
        btn.label = action or ""
        self._action = run
        self.query_one("#skip", Button).display = skip
        self.query_one("#back", Button).display = self.step > SYSTEM
        nxt = self.query_one("#next", Button)
        nxt.label = "Finish" if self.step == DONE else "Next"
        (btn if action is not None and self.step != SYSTEM else nxt).focus()

    def _busy(self, busy: bool) -> None:
        for name in _BUTTONS:
            self.query_one(f"#{name}", Button).disabled = busy
        self.query_one("#wizard-bar", ProgressBar).display = busy

    def _show(self) -> None:
        steps = Text()
        for i, name in enumerate(STEPS):
            style = "bold reverse" if i == self.step else ("#c0c0c0" if i > self.step else "")
            steps.append(f" {i + 1} {name} ", style=style)
            if i < len(STEPS) - 1:
                steps.append(">")
        self.query_one("#wizard-steps", Static).update(steps)
        self.query_one("#wizard-presets", OptionList).display = self.step == CONFIGURATION
        self.query_one("#wizard-bar", ProgressBar).display = False
        self._status("")
        getattr(self, f"_show_{STEPS[self.step].lower().replace(' ', '_')}")()

    def _show_system(self) -> None:
        if self.report is None:
            self._body("Checking this computer…")
        else:
            self._body(_checks_text(self.report.checks))
        self._buttons("Re-check", self._diagnose)

    def _show_configuration(self) -> None:
        assert self.report is not None
        best = recommend(self.presets, self.report)
        self.choice = self.choice or default_choice(self.presets, self.report)
        options = []
        for p in self.presets:
            label = f"{p.title}: {p.generator} / {p.critic}, ~{p.download_gb:g} GB"
            if best is not None and p.id == best.id:
                label += "  (recommended)"
            elif missing := unmet(p, self.report):
                label += "  ⚠ " + "; ".join(missing)
            options.append(Option(label, id=p.id))
        ol = self.query_one("#wizard-presets", OptionList)
        ol.clear_options()
        ol.add_options(options)
        ol.highlighted = [p.id for p in self.presets].index(self.choice.id)
        self._body(
            "Choose a configuration. The recommended one is the strongest this computer runs "
            "well; others are allowed but may be slow."
            if best is not None
            else "GPU memory could not be determined: choose a configuration yourself."
        )
        self._buttons()
        self._describe_choice()
        self.call_after_refresh(ol.focus)  # after the button focus set by _buttons()

    def _describe_choice(self) -> None:
        assert self.report is not None and self.choice is not None
        short = disk_shortfall_gb(self.choice, self.report)
        warnings = unmet(self.choice, self.report)
        if short > 0:
            warnings.append(f"Not enough disk space: {short:.1f} GB more needed")
        self._status("; ".join(warnings))

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        self.choice = next(p for p in self.presets if p.id == event.option.id)
        if self.step == CONFIGURATION and self.report is not None:
            self._describe_choice()

    def _show_ollama(self) -> None:
        assert self.report is not None
        info = self.report.ollama
        if info.running:
            self._body(f"Ollama {info.version} is running.")
            self._buttons()
        elif info.installed:
            self._body("Ollama is installed but not running.")
            self._buttons("Start Ollama", self._start_ollama, skip=True)
        elif self.deps.platform == "win32":
            self._body(
                "Ollama runs the models locally and is not installed yet. Agora downloads the "
                "official installer from ollama.com and starts it; finish it, then Agora "
                "continues."
            )
            self._buttons("Download and run installer", self._install, skip=True)
        else:
            self._body(install_hint(self.deps.os_name) + "\nThen press Next.")
            self._buttons(skip=True)

    def _show_ollama_settings(self) -> None:
        assert self.report is not None and self.choice is not None
        wanted = recommended_env(self.choice)
        text = Text("Recommended Ollama settings (current → recommended):\n")
        for k, v in wanted.items():
            text.append(f"  {k}: {self.report.ollama.env.get(k, '(not set)')} → {v}\n")
        if self.deps.set_env is None:
            text.append("\nSet them in your shell profile or the Ollama service, then restart it.")
            self._body(text)
            self._buttons(skip=True)
        else:
            self._body(text)
            self._buttons("Apply recommended", self._apply_settings, skip=True)

    def _show_models(self) -> None:
        assert self.report is not None and self.choice is not None
        if not self.report.ollama.running:
            self._body(
                "Ollama is not running, so models cannot be downloaded now. Finish the setup; "
                "the error box will say what is missing."
            )
            self._buttons(skip=True)
            return
        missing = missing_models(self.choice, self.report.ollama.models)
        if not missing:
            self._body(f"All models are present: {', '.join(self.choice.models)}.")
            self._buttons()
            return
        self._body(
            f"To download (~{self.choice.download_gb:g} GB in total): {', '.join(missing)}.\n"
            "You can cancel with Esc; the next download continues where it stopped."
        )
        self._buttons("Download", self._pull, skip=True)

    def _show_done(self) -> None:
        self._body("Writing the configuration…")
        self._buttons()
        self.query_one("#next", Button).disabled = True
        self._finish()

    # -- navigation ---------------------------------------------------------------------------

    def _go(self, step: int) -> None:
        self.step = max(SYSTEM, min(step, DONE))
        self._show()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        match event.button.id:
            case "back":
                self._go(self.step - 1)
            case "skip":
                self._go(self.step + 1)
            case "action" if self._action is not None:
                self._action()
            case "next" if self.step == DONE:
                self.dismiss(self.written)
            case "next" if self.report is not None:
                self._go(self.step + 1)

    def action_move(self, delta: int) -> None:
        visible = [b for b in self.query(Button) if b.display and not b.disabled]
        if not visible:
            return
        current = visible.index(self.focused) if self.focused in visible else 0
        visible[min(max(current + delta, 0), len(visible) - 1)].focus()

    def action_escape(self) -> None:
        running = [w for w in self.workers if w.group == "setup" and w.is_running]
        if running:
            for w in running:
                w.cancel()
            self._busy(False)
            self._show()
            self._status("Cancelled.")
            return
        self.dismiss(None)

    # -- work ---------------------------------------------------------------------------------

    async def _refresh(self) -> None:
        self.report = await self.deps.collect()

    @work(exclusive=True, group="setup")
    async def _diagnose(self) -> None:
        self._busy(True)
        try:
            await self._refresh()
        finally:
            self._busy(False)
        if self.step == SYSTEM:
            self._show()

    def _failed(self, message: str, retry: Callable[[], Any]) -> None:
        logger.warning("Setup step failed: %s", message)
        self._busy(False)
        self._show()
        self._buttons("Retry", retry, skip=True)
        self._status(message, error=True)

    @work(exclusive=True, group="setup")
    async def _install(self) -> None:
        self._busy(True)
        bar = self.query_one("#wizard-bar", ProgressBar)
        installer = self.deps.downloads / "OllamaSetup.exe"
        try:
            async with self.deps.client_factory() as client:
                self._status("Downloading the Ollama installer…")
                async for p in download_installer(client, self.deps.downloads):
                    bar.update(total=p.total, progress=p.done)
                launch_installer(installer, self.deps.popen)
                self._status("Finish the Ollama installer; waiting for the Ollama server…")
                if not await self.deps.wait_server(client, self.deps.base_url):
                    self._failed("Ollama was not found after the installer.", self._install)
                    return
        except (httpx.HTTPError, OSError) as e:
            self._failed(f"Cannot download the installer: {e}", self._install)
            return
        finally:
            try:
                installer.unlink(missing_ok=True)
            except OSError:  # Windows: still locked by a running installer
                logger.info("Installer %s left in place", installer)
        await self._refresh()
        self._busy(False)
        self._show()

    @work(exclusive=True, group="setup")
    async def _start_ollama(self) -> None:
        self._busy(True)
        try:
            restart_ollama(self.deps.runner, self.deps.popen, self.deps.ollama_exe)
            async with self.deps.client_factory() as client:
                ok = await self.deps.wait_server(client, self.deps.base_url)
        except OSError as e:
            self._failed(f"Cannot start Ollama: {e}", self._start_ollama)
            return
        if not ok:
            self._failed("Ollama did not start.", self._start_ollama)
            return
        await self._refresh()
        self._busy(False)
        self._show()

    @work(exclusive=True, group="setup")
    async def _apply_settings(self) -> None:
        assert self.choice is not None and self.report is not None and self.deps.set_env
        values = recommended_env(self.choice)
        self._busy(True)
        try:
            self.deps.set_env(values)
            # Ollama started by us inherits our environment, not the registry.
            self.deps.environ.update(values)
            if self.report.ollama.running:
                self._status("Restarting Ollama…")
                restart_ollama(self.deps.runner, self.deps.popen, self.deps.ollama_exe)
                async with self.deps.client_factory() as client:
                    await self.deps.wait_server(client, self.deps.base_url)
        except OSError as e:
            self._failed(f"Cannot apply the settings: {e}", self._apply_settings)
            return
        await self._refresh()
        self._busy(False)
        self._show()
        self._status("Settings applied.")

    @work(exclusive=True, group="setup")
    async def _pull(self) -> None:
        assert self.choice is not None and self.report is not None
        self._busy(True)
        bar = self.query_one("#wizard-bar", ProgressBar)
        try:
            async with self.deps.client_factory() as client:
                for model in missing_models(self.choice, self.report.ollama.models):
                    async for p in pull(model, client, self.deps.base_url):
                        if p.total:
                            bar.update(total=p.total, progress=p.completed or 0)
                        self._status(f"{model}: {p.status}")
        except PullError as e:
            self._failed(f"Download failed: {e}", self._pull)
            return
        await self._refresh()
        self._busy(False)
        self._show()
        self._status("Models downloaded.")

    @work(exclusive=True, group="setup")
    async def _finish(self) -> None:
        assert self.choice is not None
        path = self.deps.config_path
        try:
            data = build_config_data(self.choice, read_existing(path))
            bak = write_config(data, path)
        except OSError as e:
            self._failed(f"Cannot write {path}: {e}", self._finish)
            return
        self.written = path
        text = Text(f"Configuration written to {path}\n")
        if bak is not None:
            text.append(f"Previous file kept as {bak}\n")
        if self.shadowed_by is not None:
            text.append(
                f"Note: {self.shadowed_by} takes precedence at startup.\n", style="bold yellow"
            )
        await self._refresh()
        assert self.report is not None
        if self.report.ollama.running and not missing_models(
            self.choice, self.report.ollama.models
        ):
            self._body(text.append("Checking the generator model…"))
            exe = self.deps.ollama_exe or Path("ollama")
            async with self.deps.client_factory() as client:
                checks = await verify(
                    self.choice, client, self.deps.base_url, self.deps.runner, exe
                )
            text.append("\n")
            text.append_text(_checks_text(checks))
        self._body(text)
        self.query_one("#next", Button).disabled = False
        self.query_one("#next", Button).focus()
