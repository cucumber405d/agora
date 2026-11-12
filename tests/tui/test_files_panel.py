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


async def _click_label(pilot: Pilot[Any], panel: FilesPanel, name: str, dx: int) -> None:
    """Click inside the label of `name`, dx characters from the label start."""
    node = _node(panel, name)
    region = panel._get_label_region(node.line)
    assert region is not None
    content = panel.content_region.offset - panel.region.offset  # border width
    await pilot.click(
        panel,
        offset=(
            content.x + region.x + dx - panel.scroll_offset.x,
            content.y + node.line - panel.scroll_offset.y,
        ),
    )
    await pilot.pause()


async def test_click_on_checkbox_toggles_mark(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        panel = await wait_tree(pilot)
        await _click_label(pilot, panel, "b.txt", 1)  # the space inside "[ ]"
        assert app.marked_paths == {(root / "b.txt").resolve()}
        assert app.query_one("#files").border_subtitle == "Context: 1 files, 0.0k"
        await _click_label(pilot, panel, "b.txt", 0)  # the "[" of "[x]"
        assert app.marked_paths == set()


async def test_click_on_file_name_does_not_mark(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        panel = await wait_tree(pilot)
        await _click_label(pilot, panel, "b.txt", 6)  # on the name, after "[ ] " + icon
        assert app.marked_paths == set()
        assert panel.cursor_node is not None and panel.cursor_node.data.path.name == "b.txt"


def _up(panel: FilesPanel) -> Any:
    children = list(panel.root.children)
    return children[0] if children and str(children[0].label) == ".." else None


async def test_dotdot_entry_is_first_and_enter_goes_up(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        panel = await wait_tree(pilot)
        up = _up(panel)
        assert up is not None
        panel.focus()
        panel.move_cursor(up)
        await pilot.press("enter")
        await _settle(pilot, panel)
        assert Path(panel.path).resolve() == tmp_path.resolve()


async def test_click_on_dotdot_goes_up(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        panel = await wait_tree(pilot)
        up = _up(panel)
        region = panel._get_label_region(up.line)
        content = panel.content_region.offset - panel.region.offset
        await pilot.click(panel, offset=(content.x + region.x + 1, content.y + up.line))
        await _settle(pilot, panel)
        assert Path(panel.path).resolve() == tmp_path.resolve()


async def test_dotdot_cannot_be_marked(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        panel = await wait_tree(pilot)
        panel.focus()
        panel.move_cursor(_up(panel))
        await pilot.press("space")
        await pilot.pause()
        assert app.marked_paths == set()
        assert "[" not in str(panel.render_label(_up(panel), *_styles(panel)))


async def test_ctrl_pageup_works_from_prompt(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        panel = await wait_tree(pilot)
        app.query_one("#prompt").focus()
        await pilot.press("ctrl+pageup")
        await _settle(pilot, panel)
        assert Path(panel.path).resolve() == tmp_path.resolve()


async def test_backspace_in_prompt_still_edits(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        panel = await wait_tree(pilot)
        prompt = app.query_one("#prompt")
        prompt.focus()
        prompt.insert("ab")  # type: ignore[attr-defined]
        await pilot.press("backspace")
        await pilot.pause()
        assert prompt.text == "a"  # type: ignore[attr-defined]
        assert Path(panel.path).resolve() == root.resolve()


async def test_no_dotdot_at_filesystem_root(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        panel = await wait_tree(pilot)
        panel.path = Path(tmp_path.anchor)
        await _settle(pilot, panel)
        assert _up(panel) is None


async def test_title_uses_platform_separator(tmp_path: Path, monkeypatch: Any) -> None:
    from ibikus.appa.agora.tui import files_panel

    monkeypatch.setattr(files_panel, "PATH_SEP", "\\")
    deep = tmp_path / ("x" * 50) / "project"
    deep.mkdir(parents=True)
    (deep / "a.md").write_text("x", encoding="utf-8")
    app = make_app(deep)
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_tree(pilot)
        assert app.query_one(FilesPanel).border_title == "Files: …\\project"
