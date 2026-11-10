from pathlib import Path

from pydantic_ai.exceptions import ModelConnectionError
from textual.widgets import Static

from ibikus.appa.agora.config import AppConfig
from ibikus.appa.agora.llm.health import HealthIssue
from ibikus.appa.agora.tui.app import AgoraApp
from ibikus.appa.agora.tui.dialogs import ErrorScreen, ModelsScreen

from .helpers import NotifyRecorder, factory, make_project, run_prompt, wait_group, wait_tree

ISSUE = HealthIssue(
    roles=("Generator", "Critic"),
    problem="Ollama is not reachable at http://localhost:11434",
    hint="Install Ollama from https://ollama.com and start it (ollama serve).",
)


class FakeHealth:
    def __init__(self, *results: list[HealthIssue]) -> None:
        self.results = list(results)
        self.calls = 0

    async def __call__(self, config: AppConfig) -> list[HealthIssue]:
        self.calls += 1
        return self.results[min(self.calls, len(self.results)) - 1]


def _app(tmp_path: Path, health: FakeHealth, **kw: object) -> AgoraApp:
    return AgoraApp(
        AppConfig(),
        root=make_project(tmp_path),
        service_factory=factory(**kw),  # type: ignore[arg-type]
        health_check=health,
    )


def _box_text(app: AgoraApp) -> str:
    return str(app.screen.query_one("#error-body", Static).render())


async def test_startup_issue_opens_error_box(tmp_path: Path) -> None:
    app = _app(tmp_path, FakeHealth([ISSUE]))
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_group(app, "health")
        await pilot.pause()
        assert isinstance(app.screen, ErrorScreen)
        text = _box_text(app)
        assert "Generator, Critic" in text
        assert "Ollama is not reachable at http://localhost:11434" in text
        assert "ollama serve" in text


async def test_no_issues_no_box(tmp_path: Path) -> None:
    app = _app(tmp_path, FakeHealth([]))
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_group(app, "health")
        await pilot.pause()
        assert not isinstance(app.screen, ErrorScreen)


async def test_retry_closes_when_fixed(tmp_path: Path) -> None:
    health = FakeHealth([ISSUE], [])
    app = _app(tmp_path, health)
    async with app.run_test(size=(100, 30)) as pilot:
        rec = NotifyRecorder(app)
        await wait_group(app, "health")
        await pilot.pause()
        await pilot.click("#retry")
        await wait_group(app, "health")
        await pilot.pause()
        assert health.calls == 2
        assert not isinstance(app.screen, ErrorScreen)
        assert "LLM connection OK" in rec.messages


async def test_retry_still_failing_reopens_box(tmp_path: Path) -> None:
    app = _app(tmp_path, FakeHealth([ISSUE]))
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_group(app, "health")
        await pilot.pause()
        await pilot.click("#retry")
        await wait_group(app, "health")
        await pilot.pause()
        assert isinstance(app.screen, ErrorScreen)


async def test_models_button_opens_f9(tmp_path: Path) -> None:
    app = _app(tmp_path, FakeHealth([ISSUE]))
    async with app.run_test(size=(100, 40)) as pilot:
        await wait_group(app, "health")
        await pilot.pause()
        await pilot.click("#models")
        await pilot.pause()
        assert isinstance(app.screen, ModelsScreen)


async def test_escape_closes_box(tmp_path: Path) -> None:
    app = _app(tmp_path, FakeHealth([ISSUE]))
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_group(app, "health")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, ErrorScreen)


async def test_provider_error_during_run_opens_box(tmp_path: Path) -> None:
    health = FakeHealth([], [ISSUE])
    app = _app(tmp_path, health, drafts=[ModelConnectionError("m", "Connection error.")])
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_group(app, "health")
        await run_prompt(pilot, "Q")
        await wait_group(app, "health")
        await pilot.pause()
        assert isinstance(app.screen, ErrorScreen)
        assert "Ollama is not reachable" in _box_text(app)


async def test_provider_error_without_diagnosis_shows_raw_error(tmp_path: Path) -> None:
    app = _app(tmp_path, FakeHealth([]), drafts=[ModelConnectionError("m", "Connection error.")])
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_group(app, "health")
        await run_prompt(pilot, "Q")
        await wait_group(app, "health")
        await pilot.pause()
        assert isinstance(app.screen, ErrorScreen)
        assert "Connection error." in _box_text(app)


async def test_f9_apply_rechecks(tmp_path: Path) -> None:
    health = FakeHealth([])
    app = _app(tmp_path, health)
    async with app.run_test(size=(100, 40)) as pilot:
        await wait_group(app, "health")
        await wait_tree(pilot)
        await pilot.press("f9")
        await pilot.pause()
        await pilot.click("#apply")
        await wait_group(app, "health")
        assert health.calls == 2


async def test_f9_in_error_box_opens_models(tmp_path: Path) -> None:
    app = _app(tmp_path, FakeHealth([ISSUE]))
    async with app.run_test(size=(100, 40)) as pilot:
        await wait_group(app, "health")
        await pilot.pause()
        await pilot.press("f9")
        await pilot.pause()
        assert isinstance(app.screen, ModelsScreen)


async def test_arrow_keys_move_between_buttons(tmp_path: Path) -> None:
    app = _app(tmp_path, FakeHealth([ISSUE]))
    async with app.run_test(size=(100, 40)) as pilot:
        await wait_group(app, "health")
        await pilot.pause()
        assert app.focused is not None and app.focused.id == "retry"
        await pilot.press("right")
        assert app.focused.id == "models"
        await pilot.press("right")
        assert app.focused.id == "close"
        await pilot.press("right")
        assert app.focused.id == "close"  # no wrap-around
        await pilot.press("left", "left")
        assert app.focused.id == "retry"
        await pilot.press("right", "enter")
        await pilot.pause()
        assert isinstance(app.screen, ModelsScreen)


async def test_run_with_known_issue_opens_box_without_calling_llm(tmp_path: Path) -> None:
    health = FakeHealth([ISSUE], [ISSUE])
    app = _app(tmp_path, health)
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_group(app, "health")
        await pilot.pause()
        await pilot.press("escape")
        await wait_tree(pilot)
        app.query_one("#prompt").insert("Q")  # type: ignore[attr-defined]
        await pilot.press("f2")
        await wait_group(app, "health")
        await pilot.pause()
        assert isinstance(app.screen, ErrorScreen)
        assert health.calls == 2
        assert app.last_result is None and not app.run_in_progress


async def test_run_after_issue_fixed_starts_run(tmp_path: Path) -> None:
    from .helpers import wait_run

    health = FakeHealth([ISSUE], [])
    app = _app(tmp_path, health)
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_group(app, "health")
        await pilot.pause()
        await pilot.press("escape")
        await wait_tree(pilot)
        app.query_one("#prompt").insert("Q")  # type: ignore[attr-defined]
        await pilot.press("f2")
        await wait_group(app, "health")
        await pilot.pause()
        await wait_run(app)
        await pilot.pause()
        assert not isinstance(app.screen, ErrorScreen)
        assert app.last_result is not None
