from pathlib import Path
from typing import Any

import pytest
from textual.pilot import Pilot

from .helpers import make_app, make_project, run_prompt, wait_tree


def test_initial_screen(snap_compare: Any, tmp_path: Path) -> None:
    async def ready(pilot: Pilot[Any]) -> None:
        await wait_tree(pilot)

    assert snap_compare(make_app(make_project(tmp_path)), terminal_size=(100, 30), run_before=ready)


def test_after_approved_run(
    snap_compare: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # deterministic timings in the progress panel and the LLM log
    monkeypatch.setattr("ibikus.appa.agora.reflection.graph.monotonic", lambda: 0.0)
    monkeypatch.setattr("ibikus.appa.agora.tui.llm_log.monotonic", lambda: 0.0)

    async def run(pilot: Pilot[Any]) -> None:
        from ibikus.appa.agora.tui.progress import ProgressPanel

        pilot.app.query_one(ProgressPanel).progress.clock = lambda: 0.0  # deterministic timings
        await run_prompt(pilot, "Explain the difference")

    app = make_app(make_project(tmp_path), drafts=["A short **answer**."])
    assert snap_compare(app, terminal_size=(100, 30), run_before=run)


def test_help_screen(snap_compare: Any, tmp_path: Path) -> None:
    async def help_(pilot: Pilot[Any]) -> None:
        await wait_tree(pilot)
        await pilot.press("f1")
        await pilot.pause()

    assert snap_compare(make_app(make_project(tmp_path)), terminal_size=(100, 30), run_before=help_)


def test_error_box(snap_compare: Any, tmp_path: Path) -> None:
    from ibikus.appa.agora.config import AppConfig
    from ibikus.appa.agora.llm.health import HealthIssue
    from ibikus.appa.agora.tui.app import AgoraApp

    from .helpers import factory, wait_group

    issues = [
        HealthIssue(
            ("Generator", "Critic"),
            "Ollama is not reachable at http://localhost:11434",
            "Install Ollama from https://ollama.com and start it (ollama serve). "
            "If it runs on another host, set base_url in config/agora.yaml.",
        )
    ]

    async def health(cfg: AppConfig) -> list[HealthIssue]:
        return issues

    async def ready(pilot: Pilot[Any]) -> None:
        await wait_tree(pilot)
        await wait_group(pilot.app, "health")
        await pilot.pause()

    app = AgoraApp(
        AppConfig(), root=make_project(tmp_path), service_factory=factory(), health_check=health
    )
    assert snap_compare(app, terminal_size=(100, 30), run_before=ready)


def test_log_entry_dialog(snap_compare: Any, tmp_path: Path) -> None:
    from ibikus.appa.agora.reflection.events import LlmExchange
    from ibikus.appa.agora.tui.dialogs import LogEntryScreen

    entry = LlmExchange(
        role="critic",
        direction="request",
        model="qwen3:14b",
        text="[instructions]\nYou are a strict reviewer.\n\n[input]\n## Request\nрасскажи балладу",
    )

    async def open_entry(pilot: Pilot[Any]) -> None:
        await wait_tree(pilot)
        pilot.app.push_screen(LogEntryScreen(entry))
        await pilot.pause()

    assert snap_compare(
        make_app(make_project(tmp_path)), terminal_size=(100, 30), run_before=open_entry
    )


def test_document_preview(snap_compare: Any, tmp_path: Path) -> None:
    import shutil

    from .helpers import _nodes, wait_group

    root = make_project(tmp_path)
    shutil.copy(Path(__file__).parent.parent / "fixtures" / "docs" / "sample.pdf", root)

    async def preview(pilot: Pilot[Any]) -> None:
        panel = await wait_tree(pilot)
        node = next(n for n in _nodes(panel) if n.data and n.data.path.name == "sample.pdf")
        panel.focus()
        panel.move_cursor(node)
        await pilot.press("enter")
        await wait_group(pilot.app, "preview")
        await pilot.pause()

    assert snap_compare(make_app(root), terminal_size=(100, 30), run_before=preview)


def _wizard_app(tmp_path: Path) -> Any:
    from .test_setup_wizard import World, _app

    return _app(tmp_path, World())


def test_wizard_diagnostics(snap_compare: Any, tmp_path: Path) -> None:
    from .test_setup_wizard import settle

    assert snap_compare(_wizard_app(tmp_path), terminal_size=(110, 36), run_before=settle)


def test_wizard_presets(snap_compare: Any, tmp_path: Path) -> None:
    from .test_setup_wizard import press, settle

    async def presets(pilot: Pilot[Any]) -> None:
        await settle(pilot)
        await press(pilot, "next")

    assert snap_compare(_wizard_app(tmp_path), terminal_size=(110, 36), run_before=presets)
