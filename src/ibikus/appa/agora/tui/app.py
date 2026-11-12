"""Agora main application."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import ClassVar

import pyperclip
from textual import work
from textual.app import App, ComposeResult
from textual.binding import ActiveBinding, Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, TextArea

from ibikus.appa.agora.config import AppConfig, ConfigError, find_config_path, load_config
from ibikus.appa.agora.context import Context, DocumentConverter, FileContextSource
from ibikus.appa.agora.llm.factory import describe
from ibikus.appa.agora.llm.health import HealthIssue
from ibikus.appa.agora.reflection.events import LlmExchange, RunFailed, RunFinished, RunResult
from ibikus.appa.agora.reflection.export import render_run_markdown
from ibikus.appa.agora.reflection.service import ReflectionService

from .dialogs import ConfigScreen, ErrorScreen, HelpScreen, ModelsScreen, ViewerScreen
from .files_panel import FilesPanel
from .llm_log import LlmLog
from .progress import ProgressPanel
from .run_feed import RunFeed
from .setup_wizard import SetupDeps, SetupWizard, default_deps
from .status_bar import StatusBar

logger = logging.getLogger(__name__)

ServiceFactory = Callable[[AppConfig], ReflectionService]
HealthCheck = Callable[[AppConfig], Awaitable[list[HealthIssue]]]

_KEY_ORDER = ["f1", "f2", "f3", "f4", "f5", "f6", "f8", "f9", "f10", "escape"]


class _MainScreen(Screen[None]):
    """Default screen that lists bindings in Far order (F1..F10) in the footer.
    Without it, keys also bound by the focused widget (TextArea binds F6) come first."""

    @property
    def active_bindings(self) -> dict[str, ActiveBinding]:
        bindings = super().active_bindings
        rank = {k: i for i, k in enumerate(_KEY_ORDER)}
        return dict(sorted(bindings.items(), key=lambda kv: rank.get(kv[0], len(rank))))


class AgoraApp(App[None]):
    TITLE = "Agora"
    CSS_PATH = "agora.tcss"
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("f1", "help", "Help", priority=True),
        Binding("f2", "run", "Run", priority=True),
        Binding("f3", "view", "View", priority=True),
        Binding("f4", "show_config", "Config", priority=True),
        Binding("f5", "copy_result", "Copy", priority=True),
        Binding("f6", "save_result", "Save", priority=True),
        Binding("f8", "setup", "Setup", priority=True),
        Binding("f9", "models", "Models", priority=True),
        Binding("f10", "quit", "Quit", priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("ctrl+enter", "run", "Run", show=False, priority=True),
        Binding("ctrl+l", "toggle_progress", "Info", show=False, priority=True),
        Binding("ctrl+pageup", "go_parent", "Parent", show=False, priority=True),
    ]

    def __init__(
        self,
        config: AppConfig,
        root: Path,
        service_factory: ServiceFactory,
        observability_state: str = "off",
        health_check: HealthCheck | None = None,
        converter: DocumentConverter | None = None,
        start_wizard: bool = False,
        setup_deps: SetupDeps | None = None,
    ) -> None:
        super().__init__()
        self.start_wizard = start_wizard
        self._setup_deps = setup_deps
        # One converter per app: its cache survives context reloads and config changes.
        self._converter = converter or DocumentConverter(config.context.convert_timeout_s)
        self.config = config
        self.root = root.resolve()
        self._service_factory = service_factory
        self._service = service_factory(config)
        self._observability_state = observability_state
        self._health_check = health_check
        self._health_issues: list[HealthIssue] = []  # result of the last probe
        self._cancel: asyncio.Event | None = None
        self.run_in_progress = False
        self.last_result: RunResult | None = None
        self.last_prompt = ""
        self.last_context: Context | None = None

    # -- layout -------------------------------------------------------------------------------

    def get_default_screen(self) -> Screen[None]:
        return _MainScreen(id="_default")

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield FilesPanel(self.root, id="files")
                yield ProgressPanel(id="progress")
            with Vertical(id="right"):
                yield TextArea(id="prompt", soft_wrap=True, show_line_numbers=False)
                yield RunFeed(id="feed")
                yield LlmLog(id="llm-log")
        yield StatusBar(id="status")
        yield Footer()

    def on_mount(self) -> None:
        files = self.query_one(FilesPanel)
        files.border_subtitle = "Context: 0 files, 0.0k"
        self.query_one("#prompt", TextArea).border_title = "Prompt"
        self.query_one(RunFeed).border_title = "Run"
        self._refresh_status()
        self.query_one("#prompt", TextArea).focus()
        if self.start_wizard:
            self.action_setup()  # the health check runs when the wizard closes
        else:
            self.check_health()

    def _refresh_status(self) -> None:
        r = self.config.reflection
        status = self.query_one(StatusBar)
        status.set_models(describe(r.generator), describe(r.critic))
        status.set_langfuse(self._observability_state)

    # -- state --------------------------------------------------------------------------------

    @property
    def marked_paths(self) -> set[Path]:
        return set(self.query_one(FilesPanel).marked)

    def _context_source(self) -> FileContextSource:
        return FileContextSource(self.config.context, self.root, self._converter)

    async def _load_context(self, paths: list[Path]) -> Context:
        """Load (and convert) in a thread; conversion progress goes to the progress panel."""
        progress = self.query_one(ProgressPanel)

        def on_progress(done: int, total: int) -> None:
            self.call_from_thread(progress.context_progress, done, total)

        return await asyncio.to_thread(self._context_source().load, paths, on_progress)

    def rebuild_service(self, config: AppConfig) -> None:
        """Swap config and service for this session only (YAML is never rewritten).
        Raises ConfigError and keeps the current service if the new one cannot be built."""
        self._service = self._service_factory(config)
        self.config = config
        self._refresh_status()

    # -- LLM health -----------------------------------------------------------------------------

    def check_health(
        self, fallback: str | None = None, announce_ok: bool = False, run_after: bool = False
    ) -> None:
        """Probe the configured LLMs in the background; open the error box on problems.
        `fallback` is shown when a run failed but the probe found nothing specific;
        `run_after` starts the run if the probe comes back clean."""
        if self._health_check is not None:
            self._run_health(fallback, announce_ok, run_after)

    @work(exclusive=True, group="health")
    async def _run_health(self, fallback: str | None, announce_ok: bool, run_after: bool) -> None:
        assert self._health_check is not None
        issues = await self._health_check(self.config)
        self._health_issues = issues
        if not issues and run_after:
            self.action_run()
            return
        if not issues and fallback:
            issues = [
                HealthIssue(("Run",), fallback, "Details are in the log (~/.agora/logs/agora.log).")
            ]
        if issues:
            self._show_errors(issues)
        elif announce_ok:
            self.notify("LLM connection OK")

    def _show_errors(self, issues: list[HealthIssue]) -> None:
        if self._dialog_open():
            self.notify(issues[0].problem, severity="error", timeout=8)
            return
        self.push_screen(ErrorScreen(issues), self._on_error_closed)

    def _on_error_closed(self, choice: str | None) -> None:
        if choice == "retry":
            self.check_health(announce_ok=True)
        elif choice == "models":
            self.action_models()

    def copy_to_clipboard(self, text: str) -> None:
        """Copy via OSC 52 (Textual) and via the system clipboard: terminals such as Git Bash
        (mintty) ignore OSC 52 by default, so the text would otherwise never reach Windows."""
        super().copy_to_clipboard(text)
        try:
            pyperclip.copy(text)
        except pyperclip.PyperclipException:
            logger.debug("System clipboard not available; relying on OSC 52", exc_info=True)
        self.notify(f"Copied {len(text)} characters")

    def _dialog_open(self) -> bool:
        return isinstance(self.screen, ModalScreen)

    def on_files_panel_marked_changed(self, message: FilesPanel.MarkedChanged) -> None:
        self._update_context_label(sorted(message.marked))

    @work(exclusive=True, group="context")
    async def _update_context_label(self, paths: list[Path]) -> None:
        ctx = await self._load_context(paths)
        panel = self.query_one(FilesPanel)
        panel.border_subtitle = f"Context: {len(ctx.files)} files, {ctx.total_tokens / 1000:.1f}k"
        if ctx.skipped:
            self.notify(
                "Skipped: " + ", ".join(f"{s.path.name} ({s.reason})" for s in ctx.skipped),
                severity="warning",
            )

    def on_files_panel_file_opened(self, message: FilesPanel.FileOpened) -> None:
        if not self._dialog_open():
            self._preview(message.path)

    @work(exclusive=True, group="preview")
    async def _preview(self, path: Path) -> None:
        ctx = await self._load_context([path])
        if ctx.files:
            f = ctx.files[0]
            origin = f", converted from {f.source_format}" if f.source_format else ""
            title = f"{path.name} ─ ~{f.tokens} tokens{origin}"
            body = f.content
        else:
            reason = ctx.skipped[0].reason if ctx.skipped else "unreadable"
            title = f"{path.name} ─ not sent"
            body = f"**Skipped:** `{reason}`"
        if not self._dialog_open():
            self.push_screen(ViewerScreen(body, title=title))

    # -- actions ------------------------------------------------------------------------------

    def action_run(self) -> None:
        if self._dialog_open():
            return
        if self.run_in_progress:
            self.notify("A run is already in progress", severity="warning")
            return
        prompt = self.query_one("#prompt", TextArea).text
        if not prompt.strip():
            self.notify("Prompt is empty", severity="warning")
            return
        if self._health_issues:
            # The last probe found a problem: re-check instead of waiting for SDK retries.
            self.check_health(run_after=True)
            return
        paths = sorted(self.query_one(FilesPanel).marked)
        self.query_one(RunFeed).clear()
        self.last_result = None  # F3/F5/F6 must never pair the new prompt with an old answer
        self.run_in_progress = True
        self._cancel = asyncio.Event()
        self.last_prompt, self.last_context = prompt, None
        self._run(prompt, paths, self._cancel)

    def action_go_parent(self) -> None:
        if not self._dialog_open():
            self.query_one(FilesPanel).action_go_parent()

    def action_toggle_progress(self) -> None:
        panel = self.query_one(ProgressPanel)
        panel.display = not panel.display

    def action_cancel(self) -> None:
        if isinstance(self.screen, SetupWizard):
            self.screen.action_escape()  # Esc cancels a download before it closes the wizard
        elif self._dialog_open():
            self.screen.dismiss(None)
        elif self.run_in_progress and self._cancel is not None:
            self._cancel.set()

    def _open(self, screen: ModalScreen[None]) -> None:
        if not self._dialog_open():
            self.push_screen(screen)

    def _require_result(self) -> RunResult | None:
        if self.last_result is None:
            self.notify("Nothing to copy/save yet", severity="warning")
        return self.last_result

    def action_help(self) -> None:
        r = self.config.reflection
        self._open(HelpScreen(models=f"{describe(r.generator)} / {describe(r.critic)}"))

    def action_setup(self) -> None:
        if self._dialog_open():
            return
        if self.run_in_progress:
            self.notify("Wait for the run to finish", severity="warning")
            return
        deps = self._setup_deps or default_deps()
        found = find_config_path(None, os.environ, Path.cwd())
        shadowed = found if found is not None and found != deps.config_path else None

        def apply(path: Path | None) -> None:
            if path is None:
                self.check_health()
                return
            try:
                self.rebuild_service(load_config(path))
            except ConfigError as e:
                self.notify(str(e), severity="error", timeout=8)
                return
            self.check_health(announce_ok=True)

        self.push_screen(SetupWizard(deps, shadowed_by=shadowed), apply)

    def action_view(self) -> None:
        if (result := self._require_result()) is not None:
            self._open(ViewerScreen(result.final))

    def action_show_config(self) -> None:
        self._open(ConfigScreen(self.config))

    def action_copy_result(self) -> None:
        if self._dialog_open():
            return
        if (result := self._require_result()) is not None:
            self.copy_to_clipboard(result.final)

    def action_save_result(self) -> None:
        if self._dialog_open():
            return
        if (result := self._require_result()) is not None:
            now = datetime.now()
            out_dir = self.root / "agora-runs"
            path = out_dir / f"{now:%Y%m%d-%H%M%S}.md"
            try:
                out_dir.mkdir(exist_ok=True)
                path.write_text(
                    render_run_markdown(self.last_prompt, result, now), encoding="utf-8"
                )
            except OSError as e:
                self.notify(f"Cannot save: {e}", severity="error", timeout=8)
                return
            self.notify(f"Saved to {path}")

    def action_models(self) -> None:
        if isinstance(self.screen, ErrorScreen):
            self.screen.dismiss("models")  # the dismiss callback opens the models dialog
            return
        if self._dialog_open():
            return
        if self.run_in_progress:
            self.notify("Wait for the run to finish", severity="warning")
            return

        def apply(new_config: AppConfig | None) -> None:
            if new_config is None:
                return
            try:
                self.rebuild_service(new_config)
            except ConfigError as e:
                self.notify(str(e), severity="error", timeout=8)
                return
            self.check_health()

        self.push_screen(ModelsScreen(self.config), apply)

    @work(exclusive=True, group="run")
    async def _run(self, prompt: str, paths: list[Path], cancel: asyncio.Event) -> None:
        try:
            ctx = await self._load_context(paths)
        except BaseException:
            self.run_in_progress = False
            self._cancel = None
            raise
        self.last_context = ctx
        if ctx.skipped:
            self.notify(
                "Not sent: " + ", ".join(f"{s.path.name} ({s.reason})" for s in ctx.skipped),
                severity="warning",
            )
        feed = self.query_one(RunFeed)
        progress = self.query_one(ProgressPanel)
        llm_log = self.query_one(LlmLog)
        llm_log.reset()
        r = self.config.reflection
        progress.start(
            ctx,
            generator=describe(r.generator),
            critic=describe(r.critic),
            limits=f"max {r.max_iterations} iterations, threshold {r.approve_threshold}",
        )
        try:
            async for event in self._service.run(prompt, ctx, cancel):
                if isinstance(event, LlmExchange):
                    llm_log.add(event)
                    continue
                feed.apply(event)
                progress.apply(event)
                if isinstance(event, RunFinished):
                    self.last_result = event.result
                elif isinstance(event, RunFailed) and event.reason == "provider_error":
                    self.check_health(fallback=f"{event.reason}: {event.message}")
        finally:
            self.run_in_progress = False
            self._cancel = None
