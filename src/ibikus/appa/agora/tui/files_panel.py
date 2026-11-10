"""Far-like file panel: a directory tree where files can be marked with Space/Ins.

Folders are re-read from disk every time they are re-opened; Ctrl+R re-reads the whole panel;
Backspace / Ctrl+PgUp move the panel root to the parent directory."""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

from rich.style import Style
from rich.text import Text
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.widgets import DirectoryTree
from textual.widgets._directory_tree import DirEntry
from textual.widgets._tree import Tree, TreeNode


class FilesPanel(DirectoryTree):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("space", "toggle_mark", "Mark", show=False),
        Binding("insert", "toggle_mark", "Mark", show=False),
        Binding("ctrl+r", "reload_panel", "Reread", show=False),
        Binding("backspace", "go_parent", "Parent", show=False),
        Binding("ctrl+pageup", "go_parent", "Parent", show=False),
    ]

    class MarkedChanged(Message):
        def __init__(self, marked: frozenset[Path]) -> None:
            super().__init__()
            self.marked = marked

    def __init__(self, path: Path, *, id: str | None = None) -> None:
        super().__init__(path, id=id)
        self.marked: set[Path] = set()

    def on_mount(self) -> None:
        self._update_title()

    def _update_title(self) -> None:
        current = Path(self.path).resolve()
        shown = str(current)
        if len(shown) > 26:  # keep the current folder name whole, shorten the rest
            shown = f"…{os.sep}{current.name}"
        self.border_title = f"Files: {shown}"

    def _prune_marks(self) -> None:
        """Drop marks for files that no longer exist and announce the change."""
        gone = {p for p in self.marked if not p.is_file()}
        if gone:
            self.marked -= gone
            self.post_message(self.MarkedChanged(frozenset(self.marked)))

    def _on_tree_node_collapsed(self, event: Tree.NodeCollapsed[DirEntry]) -> None:
        # Forget the cached listing so that the next expand reads the folder again.
        if event.node.data is not None:
            event.node.data.loaded = False
        self._prune_marks()

    async def action_reload_panel(self) -> None:
        await self.reload()
        self._prune_marks()

    def action_go_parent(self) -> None:
        current = Path(self.path).resolve()
        if current.parent == current:
            return
        self.path = current.parent
        self._update_title()

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
