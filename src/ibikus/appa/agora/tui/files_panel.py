"""Far-like file panel: a directory tree where files can be marked with Space/Ins.

Folders are re-read from disk every time they are re-opened; Ctrl+R re-reads the whole panel;
Backspace / Ctrl+PgUp move the panel root to the parent directory."""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

from rich.style import Style
from rich.text import Text
from textual import events
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

    def _toggle(self, node: TreeNode[DirEntry] | None) -> bool:
        """Toggle the mark of a file node. Returns False for folders / empty lines."""
        if node is None or node.data is None or node.allow_expand:
            return False
        path = node.data.path.resolve()
        if path in self.marked:
            self.marked.remove(path)
        else:
            self.marked.add(path)
        self._refresh_node(node)
        self.post_message(self.MarkedChanged(frozenset(self.marked)))
        return True

    def action_toggle_mark(self) -> None:
        if self._toggle(self.cursor_node):
            self.action_cursor_down()

    async def _on_click(self, event: events.Click) -> None:
        """A click exactly on the "[ ]" box toggles the mark; elsewhere the default
        Tree behaviour (move cursor, expand folders) applies."""
        offset = event.get_content_offset(self)
        if offset is None:
            return
        line = offset.y + self.scroll_offset.y
        x = offset.x + self.scroll_offset.x
        region = self._get_label_region(line)
        node = self.get_node_at_line(line)
        if region is None or not region.x <= x < region.x + len("[ ]"):
            return
        if self._toggle(node):
            self.cursor_line = line
            event.stop()
            event.prevent_default()  # skip Tree._on_click for this click
