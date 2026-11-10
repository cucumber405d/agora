from pathlib import Path

from ibikus.appa.agora.reflection.events import LlmExchange
from ibikus.appa.agora.tui.llm_log import LlmLog, format_exchange

from .helpers import make_app, make_project, run_prompt


def _ex(direction: str, **kw: object) -> LlmExchange:
    base: dict[str, object] = {
        "role": "generator",
        "direction": direction,
        "model": "qwen3.5:9b",
        "text": "## Request\nQ " + "x" * 300,
    }
    base.update(kw)
    return LlmExchange.model_validate(base)


def test_format_request_line_and_color() -> None:
    text = format_exchange(_ex("request", tokens=3900), elapsed=0.0)
    assert text.plain.startswith("00:00 → Gen  qwen3.5:9b 3900 tk  ## Request Q xxx")
    assert len(text.plain) < 160  # one-line preview
    assert "#00ffff" in str(text.style).lower()


def test_format_colors_by_kind() -> None:
    assert "#ffffff" in str(format_exchange(_ex("response"), 1).style).lower()
    assert "#ffff55" in str(format_exchange(_ex("retry", role="critic"), 1).style).lower()
    assert "#ff5555" in str(format_exchange(_ex("error"), 1).style).lower()


def test_format_response_details() -> None:
    line = format_exchange(_ex("response", tokens=512, seconds=16.8, finish="stop"), 16).plain
    assert line.startswith("00:16 ← Gen  512 tk 16.8s stop  ")


async def test_log_panel_after_run_and_full_text(tmp_path: Path) -> None:
    from textual.widgets import TextArea

    from ibikus.appa.agora.tui.dialogs import LogEntryScreen

    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(120, 50)) as pilot:
        await run_prompt(pilot, "Q")
        log = app.query_one(LlmLog)
        assert len(log.entries) == 4
        log.focus()
        log.index = 0
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, LogEntryScreen)
        assert "## Request\nQ" in app.screen.query_one(TextArea).text
        await pilot.press("escape")


async def test_log_cleared_on_new_run(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(120, 50)) as pilot:
        await run_prompt(pilot, "Q")
        await run_prompt(pilot, "Q2")
        assert len(app.query_one(LlmLog).entries) == 4


async def test_run_failure_is_red_line(tmp_path: Path) -> None:
    from pydantic_ai.exceptions import ModelConnectionError

    app = make_app(make_project(tmp_path), drafts=[ModelConnectionError("m", "refused")])
    async with app.run_test(size=(120, 50)) as pilot:
        await run_prompt(pilot, "Q")
        log = app.query_one(LlmLog)
        assert [e.direction for e in log.entries] == ["request", "error"]
