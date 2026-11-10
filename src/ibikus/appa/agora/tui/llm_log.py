"""LLM log: every request to and response from the models, colour-coded; Enter opens the
full text of the selected entry."""

from __future__ import annotations

from time import monotonic

from rich.text import Text
from textual.widgets import Label, ListItem, ListView

from ibikus.appa.agora.reflection.events import LlmExchange

COLORS = {"request": "#00ffff", "response": "#ffffff", "retry": "#ffff55", "error": "#ff5555"}
_ARROWS = {"request": "→", "response": "←", "retry": "→", "error": "✕"}
_ROLES = {"generator": "Gen ", "critic": "Crit"}
_PREVIEW = 100


def _mmss(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60:02d}:{s % 60:02d}"


def format_exchange(e: LlmExchange, elapsed: float) -> Text:
    """One-line, colour-coded summary of an exchange."""
    source = e.preview
    if source is None:
        # Skip the (always identical) instructions and show what is specific to this call.
        source = e.text.split("[input]\n", 1)[1] if "[input]\n" in e.text else e.text
    preview = " ".join(source.split())[:_PREVIEW]
    if e.direction == "request":
        detail = f"{e.model} {e.tokens} tk" if e.tokens is not None else e.model
    elif e.direction == "response":
        bits = [f"{e.tokens} tk" if e.tokens is not None else None]
        bits.append(f"{e.seconds:.1f}s" if e.seconds is not None else None)
        bits.append(e.finish)
        detail = " ".join(b for b in bits if b)
    else:
        detail = e.direction
    line = f"{_mmss(elapsed)} {_ARROWS[e.direction]} {_ROLES[e.role]} {detail}  {preview}"
    return Text(line, style=COLORS[e.direction], no_wrap=True, overflow="ellipsis")


class LlmLog(ListView):
    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.entries: list[LlmExchange] = []
        self._t0 = monotonic()

    def on_mount(self) -> None:
        self.border_title = "LLM log"

    def reset(self) -> None:
        self.clear()
        self.entries = []
        self._t0 = monotonic()

    def add(self, exchange: LlmExchange) -> None:
        self.entries.append(exchange)
        self.append(ListItem(Label(format_exchange(exchange, monotonic() - self._t0))))
        self.scroll_end(animate=False)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        from .dialogs import LogEntryScreen

        index = self.index
        if index is not None and 0 <= index < len(self.entries):
            event.stop()
            self.app.push_screen(LogEntryScreen(self.entries[index]))
