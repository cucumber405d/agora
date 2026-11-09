from pathlib import Path
from typing import Any

from textual.pilot import Pilot

from .helpers import make_app, make_project, run_prompt, wait_tree


def test_initial_screen(snap_compare: Any, tmp_path: Path) -> None:
    async def ready(pilot: Pilot[Any]) -> None:
        await wait_tree(pilot)

    assert snap_compare(make_app(make_project(tmp_path)), terminal_size=(100, 30), run_before=ready)


def test_after_approved_run(snap_compare: Any, tmp_path: Path) -> None:
    async def run(pilot: Pilot[Any]) -> None:
        await run_prompt(pilot, "Explain the difference")

    app = make_app(make_project(tmp_path), drafts=["A short **answer**."])
    assert snap_compare(app, terminal_size=(100, 30), run_before=run)


def test_help_screen(snap_compare: Any, tmp_path: Path) -> None:
    async def help_(pilot: Pilot[Any]) -> None:
        await wait_tree(pilot)
        await pilot.press("f1")
        await pilot.pause()

    assert snap_compare(make_app(make_project(tmp_path)), terminal_size=(100, 30), run_before=help_)
