"""Render README screenshots from the real UI with fake models (SVG, then PNG via Playwright).

Usage: uv run python scripts/screenshots.py [out_dir]   (default: docs/screenshots)
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from textual.widgets import TextArea  # noqa: E402

from ibikus.appa.agora.config import AppConfig  # noqa: E402
from ibikus.appa.agora.setup.config_writer import build_config_data  # noqa: E402
from ibikus.appa.agora.setup.presets import load_presets  # noqa: E402
from ibikus.appa.agora.tui.app import AgoraApp  # noqa: E402
from ibikus.appa.agora.tui.files_panel import FilesPanel  # noqa: E402
from tests.tui.helpers import factory, wait_group, wait_run  # noqa: E402
from tests.tui.test_setup_wizard import World, press, settle  # noqa: E402

SIZE = (130, 40)
QUALITY = next(p for p in load_presets() if p.id == "quality")
CONFIG = AppConfig.model_validate(build_config_data(QUALITY))
ANSWER = (
    "**Reflection** means a second model checks the first one's draft:\n\n"
    "1. the generator writes an answer at a high temperature;\n"
    "2. the critic scores it against the request and the context;\n"
    "3. the loop repeats until the score reaches the threshold."
)


def _project(tmp: Path) -> Path:
    root = tmp / "my-project"
    (root / "docs").mkdir(parents=True)
    (root / "README.md").write_text("# My project\n", encoding="utf-8")
    shutil.copy(ROOT / "tests" / "fixtures" / "docs" / "sample.pdf", root / "report.pdf")
    shutil.copy(ROOT / "tests" / "fixtures" / "docs" / "sample.docx", root / "notes.docx")
    return root


async def _mark(app: Any, pilot: Any, name: str) -> None:
    panel = app.query_one(FilesPanel)
    for _ in range(50):
        await pilot.pause(0.02)
        nodes = [n for n in _all(panel) if n.data and n.data.path.name == name]
        if nodes:
            panel.move_cursor(nodes[0])
            panel.focus()
            await pilot.press("space")
            await wait_group(app, "context")
            return


def _all(panel: Any) -> list[Any]:
    out, stack = [], [panel.root]
    while stack:
        node = stack.pop()
        out.append(node)
        stack.extend(node.children)
    return out


async def main_screen(tmp: Path, out: Path) -> None:
    app = AgoraApp(CONFIG, root=_project(tmp), service_factory=factory(drafts=[ANSWER]))
    async with app.run_test(size=SIZE) as pilot:
        await _mark(app, pilot, "report.pdf")
        prompt = app.query_one("#prompt", TextArea)
        prompt.focus()
        prompt.insert("Summarise the report and explain the reflection loop.")
        await pilot.press("f2")
        await pilot.pause()
        await wait_run(app)
        await pilot.pause(0.2)
        app.save_screenshot("main.svg", str(out))


async def wizard_screen(tmp: Path, out: Path) -> None:
    world = World()
    app = AgoraApp(
        AppConfig(),
        root=_project(tmp / "w"),
        service_factory=factory(),
        start_wizard=True,
        setup_deps=world.deps(tmp),
    )
    async with app.run_test(size=SIZE) as pilot:
        await settle(pilot)
        await press(pilot, "next")
        await pilot.pause(0.2)
        app.save_screenshot("wizard.svg", str(out))


async def preview_screen(tmp: Path, out: Path) -> None:
    app = AgoraApp(CONFIG, root=_project(tmp / "p"), service_factory=factory())
    async with app.run_test(size=SIZE) as pilot:
        panel = app.query_one(FilesPanel)
        for _ in range(50):
            await pilot.pause(0.02)
            nodes = [n for n in _all(panel) if n.data and n.data.path.name == "report.pdf"]
            if nodes:
                break
        panel.move_cursor(nodes[0])
        panel.focus()
        await pilot.press("enter")
        await wait_group(app, "preview")
        await pilot.pause(0.2)
        app.save_screenshot("document-preview.svg", str(out))


def to_png(out: Path) -> None:
    """Convert the SVGs to PNG (GitHub renders Textual's SVG fonts poorly). Needs Playwright;
    without it the SVGs are kept."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed: SVG files kept; convert them with Playwright/Chromium.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=2)
        for svg in sorted(out.glob("*.svg")):
            page.goto(svg.as_uri())
            page.wait_for_timeout(500)  # web font
            page.locator("svg").first.screenshot(path=str(svg.with_suffix(".png")))
            svg.unlink()
        browser.close()


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "screenshots"
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t) / "demo"  # shown in the files panel title
        asyncio.run(main_screen(tmp, out))
        asyncio.run(wizard_screen(tmp, out))
        asyncio.run(preview_screen(tmp, out))
    to_png(out)


if __name__ == "__main__":
    main()
