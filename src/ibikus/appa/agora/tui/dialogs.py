"""Modal dialogs: help, answer viewer, config view, model switch."""

from __future__ import annotations

from typing import ClassVar, get_args

from pydantic import ValidationError
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, MarkdownViewer, Select, Static, TextArea

from ibikus.appa.agora.config import AppConfig, ModelConfig, Provider
from ibikus.appa.agora.llm.health import HealthIssue

HELP_ROWS = [
    ("F1", "Help"),
    ("F2 / Ctrl+Enter", "Run the reflection loop"),
    ("F3", "View final answer (Markdown)"),
    ("F4", "Show active configuration"),
    ("F5", "Copy final answer to clipboard"),
    ("F6", "Save run as Markdown to ./agora-runs/"),
    ("F9", "Switch models / temperatures (this session only)"),
    ("F10", "Quit"),
    ("Esc", "Cancel run / close dialog"),
    ("← / →, Enter", "Choose and press a dialog button"),
    ("Space / Ins / click [ ]", "Mark file for context (file panel)"),
    ("Ctrl+R", "Re-read the file panel from disk"),
    ("Ctrl+L", "Show / hide the progress panel"),
    ("Backspace / Ctrl+PgUp", "File panel: go to the parent directory"),
]


class _Dialog(ModalScreen[None]):
    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "close", "Close")]

    def action_close(self) -> None:
        self.dismiss(None)


class HelpScreen(_Dialog):
    def compose(self) -> ComposeResult:
        body = "\n".join(f"{k:<18} {v}" for k, v in HELP_ROWS)
        box = Static(Text(body), id="help-body", classes="dialog")
        box.border_title = "Help"
        yield box


class ViewerScreen(_Dialog):
    def __init__(self, markdown: str) -> None:
        super().__init__()
        self._markdown = markdown

    def compose(self) -> ComposeResult:
        viewer = MarkdownViewer(self._markdown, show_table_of_contents=False, classes="dialog")
        viewer.border_title = "Final answer"
        yield viewer


class ConfigScreen(_Dialog):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config

    def compose(self) -> ComposeResult:
        area = TextArea(self._config.model_dump_json(indent=2), read_only=True, classes="dialog")
        area.border_title = "Configuration (read-only)"
        yield area


_PROVIDERS: list[tuple[str, str]] = [(p, p) for p in get_args(Provider)]


class ModelsScreen(ModalScreen[AppConfig | None]):
    """Edit generator and critic models for this session. YAML is never rewritten."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel_dialog", "Close")]

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config

    def _role(self, prefix: str, title: str, cfg: ModelConfig) -> ComposeResult:
        yield Label(title, classes="role-title")
        with Grid(classes="role"):
            yield Label("Provider")
            yield Select(_PROVIDERS, value=cfg.provider, allow_blank=False, id=f"{prefix}-provider")
            yield Label("Model")
            yield Input(cfg.name, id=f"{prefix}-name")
            yield Label("Temperature")
            yield Input(f"{cfg.temperature:g}", id=f"{prefix}-temp")

    def compose(self) -> ComposeResult:
        r = self._config.reflection
        with Vertical(classes="dialog", id="models") as box:
            box.border_title = "Models (session only)"
            yield from self._role("gen", "Generator", r.generator)
            yield from self._role("critic", "Critic", r.critic)
            yield Label("", id="models-error")
            with Horizontal(id="models-buttons"):
                yield Button("Apply", id="apply", variant="primary")
                yield Button("Cancel", id="cancel")

    def _read(self, prefix: str, base: ModelConfig) -> ModelConfig:
        data = base.model_dump()
        provider = self.query_one(f"#{prefix}-provider", Select).value
        if provider != base.provider:
            data["base_url"] = None  # an Ollama URL must not follow a switch to a cloud provider
        data["provider"] = provider
        data["name"] = self.query_one(f"#{prefix}-name", Input).value.strip()
        data["temperature"] = self.query_one(f"#{prefix}-temp", Input).value.strip()
        return ModelConfig.model_validate(data)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        r = self._config.reflection
        try:
            gen = self._read("gen", r.generator)
            critic = self._read("critic", r.critic)
        except ValidationError as e:
            msg = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
            self.query_one("#models-error", Label).update(Text(msg))
            return
        reflection = r.model_copy(update={"generator": gen, "critic": critic})
        self.dismiss(self._config.model_copy(update={"reflection": reflection}))

    def action_cancel_dialog(self) -> None:
        self.dismiss(None)


class ErrorScreen(ModalScreen[str | None]):
    """Red Far-style error box: what is missing for the LLMs and how to fix it.
    Dismisses with "retry", "models" or None (close)."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close", "Close"),
        Binding("left", "move(-1)", show=False),
        Binding("right", "move(1)", show=False),
    ]
    _BUTTONS = ("retry", "models", "close")

    def __init__(self, issues: list[HealthIssue]) -> None:
        super().__init__()
        self._issues = issues

    def _body(self) -> Text:
        text = Text()
        for i, issue in enumerate(self._issues):
            if i:
                text.append("\n")
            text.append(f"{', '.join(issue.roles)}: ", style="bold")
            text.append(issue.problem + "\n", style="bold")
            text.append(f"  → {issue.hint}\n")
        return text

    def compose(self) -> ComposeResult:
        with Vertical(id="error-box") as box:
            box.border_title = "LLM not available"
            yield Static(self._body(), id="error-body")
            with Horizontal(id="error-buttons"):
                yield Button("Retry", id="retry")
                yield Button("Models (F9)", id="models")
                yield Button("Close", id="close")

    def on_mount(self) -> None:
        self.query_one("#retry", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None if event.button.id == "close" else event.button.id)

    def action_move(self, delta: int) -> None:
        """Arrow keys move focus between the buttons (no wrap-around), as in Far dialogs."""
        current = self.focused.id if self.focused is not None else None
        index = self._BUTTONS.index(current) if current in self._BUTTONS else 0
        target = min(max(index + delta, 0), len(self._BUTTONS) - 1)
        self.query_one(f"#{self._BUTTONS[target]}", Button).focus()

    def action_close(self) -> None:
        self.dismiss(None)
