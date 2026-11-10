from pathlib import Path
from typing import Any

from textual.pilot import Pilot

from ibikus.appa.agora.tui.files_panel import FilesPanel

from .helpers import _nodes, make_app, make_project, mark, wait_tree


def _names(panel: FilesPanel) -> set[str]:
    return {n.data.path.name for n in _nodes(panel) if n.data is not None}


def _node(panel: FilesPanel, name: str) -> Any:
    return next(n for n in _nodes(panel) if n.data is not None and n.data.path.name == name)


async def _settle(pilot: Pilot[Any], panel: FilesPanel) -> None:
    for _ in range(10):
        await pilot.pause(0.05)


async def test_reopening_folder_rereads_it(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    (root / "sub").mkdir()
    (root / "sub" / "old.md").write_text("x", encoding="utf-8")
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        panel = await wait_tree(pilot)
        sub = _node(panel, "sub")
        sub.expand()
        await _settle(pilot, panel)
        assert "old.md" in _names(panel)
        (root / "sub" / "new.md").write_text("y", encoding="utf-8")
        sub.collapse()
        await pilot.pause()
        sub.expand()
        await _settle(pilot, panel)
        assert "new.md" in _names(panel)


async def test_ctrl_r_rereads_panel(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        panel = await wait_tree(pilot)
        (root / "c.md").write_text("z", encoding="utf-8")
        panel.focus()
        await pilot.press("ctrl+r")
        await _settle(pilot, panel)
        assert "c.md" in _names(panel)


async def test_marks_survive_reload(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        await mark(pilot, "a.md")
        panel = app.query_one(FilesPanel)
        await pilot.press("ctrl+r")
        await _settle(pilot, panel)
        assert app.marked_paths == {(root / "a.md").resolve()}
        assert "[x]" in str(panel.render_label(_node(panel, "a.md"), *_styles(panel)))


def _styles(panel: FilesPanel) -> tuple[Any, Any]:
    from rich.style import Style

    return Style(), Style()


async def test_deleted_marked_file_is_unmarked_on_reload(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        await mark(pilot, "a.md")
        panel = app.query_one(FilesPanel)
        (root / "a.md").unlink()
        await pilot.press("ctrl+r")
        await _settle(pilot, panel)
        assert app.marked_paths == set()
        assert app.query_one("#files").border_subtitle == "Context: 0 files, 0.0k"


async def test_backspace_goes_to_parent(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    (tmp_path / "sibling.md").write_text("s", encoding="utf-8")
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        panel = await wait_tree(pilot)
        panel.focus()
        await pilot.press("backspace")
        await _settle(pilot, panel)
        assert Path(panel.path).resolve() == tmp_path.resolve()
        assert {"project", "sibling.md"} <= _names(panel)
        assert str(tmp_path.name) in str(panel.border_title)


async def test_ctrl_pageup_goes_to_parent_and_keeps_marks(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        await mark(pilot, "a.md")
        panel = app.query_one(FilesPanel)
        await pilot.press("ctrl+pageup")
        await _settle(pilot, panel)
        assert Path(panel.path).resolve() == tmp_path.resolve()
        assert app.marked_paths == {(root / "a.md").resolve()}


async def test_parent_of_filesystem_root_is_noop(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        panel = await wait_tree(pilot)
        panel.path = Path(tmp_path.anchor)
        await _settle(pilot, panel)
        panel.focus()
        await pilot.press("backspace")
        await _settle(pilot, panel)
        assert Path(panel.path) == Path(tmp_path.anchor)
