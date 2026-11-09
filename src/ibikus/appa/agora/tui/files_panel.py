"""Far-like file panel: a directory tree where files can be marked with Space/Ins."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from rich.style import Style
from rich.text import Text
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.widgets import DirectoryTree
from textual.widgets._directory_tree import DirEntry
from textual.widgets._tree import TreeNode


class FilesPanel(DirectoryTree):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("space", "toggle_mark", "Mark", show=False),
        Binding("insert", "toggle_mark", "Mark", show=False),
    ]

    class MarkedChanged(Message):
        def __init__(self, marked: frozenset[Path]) -> None:
            super().__init__()
            self.marked = marked

    def __init__(self, path: Path, *, id: str | None = None) -> None:
        super().__init__(path, id=id)
        self.marked: set[Path] = set()

    def render_label(self, node: TreeNode[DirEntry], base_style: Style, style: Style) -> Text:
        label = super().render_label(node, base_style, style)
        if node.data is None or node.allow_expand:
            return label
        prefix = "[x] " if node.data.path.resolve() in self.marked else "[ ] "
        return Text.assemble(prefix, label)

    def action_toggle_mark(self) -> None:
        node = self.cursor_node
        if node is None or node.data is None or node.allow_expand:
            return
        path = node.data.path.resolve()
        if path in self.marked:
            self.marked.remove(path)
        else:
            self.marked.add(path)
        self._refresh_node(node)
        self.post_message(self.MarkedChanged(frozenset(self.marked)))
        self.action_cursor_down()
