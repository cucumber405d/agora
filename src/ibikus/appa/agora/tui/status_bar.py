"""Status line: active models and Langfuse state."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

_LANGFUSE_ICON = {"on": "●", "off": "○", "error": "✕"}


class StatusBar(Static):
    def __init__(self, *, id: str | None = None) -> None:
        super().__init__("", id=id)
        self._gen = self._critic = ""
        self._langfuse = "off"

    def set_models(self, gen: str, critic: str) -> None:
        self._gen, self._critic = gen, critic
        self._refresh_text()

    def set_langfuse(self, state: str) -> None:
        self._langfuse = state
        self._refresh_text()

    def _refresh_text(self) -> None:
        icon = _LANGFUSE_ICON.get(self._langfuse, "?")
        self.update(Text(f" Gen: {self._gen} │ Critic: {self._critic} │ Langfuse {icon}"))
