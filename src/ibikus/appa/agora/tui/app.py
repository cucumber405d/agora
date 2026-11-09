"""Agora main application."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, TextArea

from ibikus.appa.agora.config import AppConfig
from ibikus.appa.agora.context import Context, FileContextSource
from ibikus.appa.agora.llm.factory import describe
from ibikus.appa.agora.reflection.events import RunFinished, RunResult
from ibikus.appa.agora.reflection.service import ReflectionService

from .files_panel import FilesPanel
from .run_feed import RunFeed
from .status_bar import StatusBar

ServiceFactory = Callable[[AppConfig], ReflectionService]


class AgoraApp(App[None]):
    TITLE = "Agora"
    CSS_PATH = "agora.tcss"
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("f2", "run", "Run", priority=True),
        Binding("ctrl+enter", "run", "Run", show=False, priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("f10", "quit", "Quit", priority=True),
    ]

    def __init__(
        self,
        config: AppConfig,
        root: Path,
        service_factory: ServiceFactory,
        observability_state: str = "off",
    ) -> None:
        super().__init__()
        self.config = config
        self.root = root.resolve()
        self._service_factory = service_factory
        self._service = service_factory(config)
        self._observability_state = observability_state
        self._cancel: asyncio.Event | None = None
        self.run_in_progress = False
        self.last_result: RunResult | None = None
        self.last_prompt = ""
        self.last_context: Context | None = None

    # -- layout -------------------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            yield FilesPanel(self.root, id="files")
            with Vertical(id="right"):
                yield TextArea(id="prompt", soft_wrap=True, show_line_numbers=False)
                yield RunFeed(id="feed")
        yield StatusBar(id="status")
        yield Footer()

    def on_mount(self) -> None:
        files = self.query_one(FilesPanel)
        files.border_title = "Files"
        files.border_subtitle = "Context: 0 files, 0.0k"
        self.query_one("#prompt", TextArea).border_title = "Prompt"
        self.query_one(RunFeed).border_title = "Run"
        self._refresh_status()
        self.query_one("#prompt", TextArea).focus()

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
        return FileContextSource(self.config.context, self.root)

    def rebuild_service(self, config: AppConfig) -> None:
        """Swap config and service for this session only (YAML is never rewritten)."""
        self._service = self._service_factory(config)
        self.config = config
        self._refresh_status()

    def on_files_panel_marked_changed(self, message: FilesPanel.MarkedChanged) -> None:
        ctx = self._context_source().load(sorted(message.marked))
        panel = self.query_one(FilesPanel)
        panel.border_subtitle = f"Context: {len(ctx.files)} files, {ctx.total_tokens / 1000:.1f}k"
        if ctx.skipped:
            self.notify(
                "Skipped: " + ", ".join(f"{s.path.name} ({s.reason})" for s in ctx.skipped),
                severity="warning",
            )

    # -- actions ------------------------------------------------------------------------------

    def action_run(self) -> None:
        if self.run_in_progress:
            self.notify("A run is already in progress", severity="warning")
            return
        prompt = self.query_one("#prompt", TextArea).text
        if not prompt.strip():
            self.notify("Prompt is empty", severity="warning")
            return
        ctx = self._context_source().load(sorted(self.query_one(FilesPanel).marked))
        if ctx.skipped:
            self.notify(
                "Not sent: " + ", ".join(f"{s.path.name} ({s.reason})" for s in ctx.skipped),
                severity="warning",
            )
        self.query_one(RunFeed).clear()
        self.run_in_progress = True
        self._cancel = asyncio.Event()
        self.last_prompt, self.last_context = prompt, ctx
        self._run(prompt, ctx, self._cancel)

    def action_cancel(self) -> None:
        if self.run_in_progress and self._cancel is not None:
            self._cancel.set()

    @work(exclusive=True, group="run")
    async def _run(self, prompt: str, ctx: Context, cancel: asyncio.Event) -> None:
        feed = self.query_one(RunFeed)
        try:
            async for event in self._service.run(prompt, ctx, cancel):
                feed.apply(event)
                if isinstance(event, RunFinished):
                    self.last_result = event.result
        finally:
            self.run_in_progress = False
            self._cancel = None
