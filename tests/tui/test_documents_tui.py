import shutil
import time
from pathlib import Path

from ibikus.appa.agora.config import AppConfig
from ibikus.appa.agora.context import DocumentConverter
from ibikus.appa.agora.tui.app import AgoraApp
from ibikus.appa.agora.tui.dialogs import ViewerScreen
from ibikus.appa.agora.tui.progress import ProgressPanel

from .helpers import _nodes, factory, make_project, mark, run_prompt, wait_group, wait_tree

DOCS = Path(__file__).parent.parent / "fixtures" / "docs"


def _project(tmp_path: Path) -> Path:
    root = make_project(tmp_path)
    shutil.copy(DOCS / "sample.pdf", root / "sample.pdf")
    shutil.copy(DOCS / "old.doc", root / "old.doc")
    return root


def _app(root: Path, converter: DocumentConverter | None = None) -> AgoraApp:
    return AgoraApp(AppConfig(), root=root, service_factory=factory(), converter=converter)


async def test_marking_document_counts_tokens(tmp_path: Path) -> None:
    app = _app(_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        await mark(pilot, "sample.pdf")
        await wait_group(app, "context")
        await pilot.pause()
        assert app.query_one("#files").border_subtitle == "Context: 1 files, 0.0k"


async def test_run_waits_for_conversion(tmp_path: Path) -> None:
    def slow(path: Path) -> str:
        time.sleep(0.3)
        return "converted text"

    app = _app(_project(tmp_path), DocumentConverter(convert=slow))
    async with app.run_test(size=(100, 30)) as pilot:
        await mark(pilot, "sample.pdf")
        await run_prompt(pilot, "Q")
        assert app.last_context is not None
        assert [f.content for f in app.last_context.files] == ["converted text"]
        assert any(
            "Context: converting 1/1" in line for line in app.query_one(ProgressPanel).history
        )


async def _open(pilot: object, app: AgoraApp, name: str) -> None:
    panel = await wait_tree(pilot)  # type: ignore[arg-type]
    node = next(n for n in _nodes(panel) if n.data and n.data.path.name == name)
    panel.focus()
    panel.move_cursor(node)
    await pilot.press("enter")  # type: ignore[attr-defined]
    await wait_group(app, "preview")
    await pilot.pause()  # type: ignore[attr-defined]


async def test_enter_on_document_opens_preview(tmp_path: Path) -> None:
    app = _app(_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        await _open(pilot, app, "sample.pdf")
        assert isinstance(app.screen, ViewerScreen)
        assert "sample.pdf" in app.screen.title_text
        assert "tokens" in app.screen.title_text
        assert "Agora sample document PDF" in app.screen.markdown


async def test_enter_on_legacy_doc_shows_reason(tmp_path: Path) -> None:
    app = _app(_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        await _open(pilot, app, "old.doc")
        assert isinstance(app.screen, ViewerScreen)
        assert "legacy_format" in app.screen.markdown
