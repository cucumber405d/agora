from pathlib import Path

from pydantic_ai.exceptions import ModelConnectionError

from ibikus.appa.agora.tui.run_feed import RunFeed

from .helpers import (
    NotifyRecorder,
    make_app,
    make_project,
    mark,
    run_prompt,
    wait_run,
    wait_tree,
)


def _feed_text(app: object) -> str:
    return app.query_one(RunFeed).plain_text()  # type: ignore[attr-defined]


async def test_mark_file_updates_context_label(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        await mark(pilot, "a.md")
        assert app.query_one("#files").border_subtitle == "Context: 1 files, 0.0k"
        assert app.marked_paths == {make_project_root(tmp_path) / "a.md"}


def make_project_root(tmp_path: Path) -> Path:
    return (tmp_path / "project").resolve()


async def test_run_shows_iterations_and_final(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        await run_prompt(pilot, "Q")
        text = _feed_text(app)
        assert "Iter 1" in text
        assert "Final (approved, score 9)" in text
        assert "Answer" in text
        assert app.last_result is not None and app.last_prompt == "Q"
        assert not app.run_in_progress


async def test_marked_file_goes_into_context(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        await mark(pilot, "a.md")
        await run_prompt(pilot, "Q")
        assert app.last_context is not None
        assert [f.path.as_posix() for f in app.last_context.files] == ["a.md"]


async def test_empty_prompt_notifies(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        rec = NotifyRecorder(app)
        await wait_tree(pilot)
        await pilot.press("f2")
        await pilot.pause()
        assert "Prompt is empty" in rec.messages
        assert _feed_text(app) == ""


async def test_second_run_while_running_is_rejected(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path), drafts=["AAAABBBB"], chunk_delay=5)
    async with app.run_test(size=(100, 30)) as pilot:
        rec = NotifyRecorder(app)
        await wait_tree(pilot)
        app.query_one("#prompt").insert("Q")  # type: ignore[attr-defined]
        await pilot.press("f2")
        await pilot.pause(0.1)
        await pilot.press("f2")
        await pilot.pause()
        assert "A run is already in progress" in rec.messages
        await pilot.press("escape")
        await wait_run(app)


async def test_escape_cancels(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path), drafts=["AAAABBBB"], chunk_delay=5)
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_tree(pilot)
        app.query_one("#prompt").insert("Q")  # type: ignore[attr-defined]
        await pilot.press("f2")
        await pilot.pause(0.1)
        await pilot.press("escape")
        await wait_run(app)
        await pilot.pause()
        assert "cancelled: Run cancelled" in _feed_text(app)
        assert not app.run_in_progress


async def test_provider_error_shown_not_crash(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path), drafts=[ModelConnectionError("m", "refused")])
    async with app.run_test(size=(100, 30)) as pilot:
        await run_prompt(pilot, "Q")
        assert "provider_error" in _feed_text(app)
        assert app.run_in_progress is False
        assert app.return_code is None  # still running


async def test_status_bar_shows_models(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        status = str(app.query_one("#status").render())
        assert "Gen: ollama/qwen2.5:7b t=0.9" in status
        assert "Critic: anthropic/claude-haiku-4-5 t=0.1" in status
        assert "Langfuse ○" in status


async def test_markup_in_model_output_is_not_interpreted(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path), drafts=["[bold]x[/bold] [link=y]"])
    async with app.run_test(size=(100, 30)) as pilot:
        await run_prompt(pilot, "Q")
        assert "[bold]x[/bold] [link=y]" in _feed_text(app)


async def test_critic_failure_shows_warning_and_final(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path), drafts=["Answer"], critiques=["**Score:** 8"])
    async with app.run_test(size=(100, 30)) as pilot:
        await run_prompt(pilot, "Q")
        text = _feed_text(app)
        assert "critique failed:" in text
        assert "Final (critic_failed, score 0)" in text
        assert app.last_result is not None and app.last_result.final == "Answer"


async def test_feed_shows_full_critique(tmp_path: Path) -> None:
    from tests.reflection.fakes import c

    crit = c(5, issues=["Invented facts"], suggestions=["Stick to the CV"], feedback="Too loose.")
    app = make_app(make_project(tmp_path), drafts=["A", "B"], critiques=[crit, c(9, approved=True)])
    async with app.run_test(size=(100, 30)) as pilot:
        await run_prompt(pilot, "Q")
        text = _feed_text(app)
        assert "critique: score 5/10" in text
        assert "Too loose." in text
        assert "Issues:\n  - Invented facts" in text
        assert "Suggestions:\n  - Stick to the CV" in text


async def test_iterations_collapse_when_final_arrives(tmp_path: Path) -> None:
    from textual.widgets import Collapsible

    from tests.reflection.fakes import c

    app = make_app(make_project(tmp_path), drafts=["A", "B"], critiques=[c(5), c(9, approved=True)])
    async with app.run_test(size=(100, 30)) as pilot:
        await run_prompt(pilot, "Q")
        boxes = list(app.query_one(RunFeed).query(Collapsible))
        assert len(boxes) == 2
        assert all(b.collapsed for b in boxes)


async def test_critique_stays_visible_after_final(tmp_path: Path) -> None:
    from textual.widgets import Collapsible

    from tests.reflection.fakes import c

    app = make_app(
        make_project(tmp_path), drafts=["A"], critiques=[c(9, approved=True, feedback="Solid.")]
    )
    async with app.run_test(size=(100, 30)) as pilot:
        await run_prompt(pilot, "Q")
        critique = app.query_one(RunFeed).query_one(".critique")
        assert "Solid." in str(critique.render())
        assert not any(isinstance(a, Collapsible) for a in critique.ancestors)
