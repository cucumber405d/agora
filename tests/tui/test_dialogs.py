from pathlib import Path

from textual.widgets import Input

from ibikus.appa.agora.config import AppConfig
from ibikus.appa.agora.tui.app import AgoraApp
from ibikus.appa.agora.tui.dialogs import ConfigScreen, HelpScreen, ModelsScreen, ViewerScreen

from .helpers import NotifyRecorder, factory, make_app, make_project, run_prompt, wait_tree


async def test_f6_saves_markdown(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        await run_prompt(pilot, "Q")
        await pilot.press("f6")
        await pilot.pause()
        files = list((root / "agora-runs").glob("*.md"))
        assert len(files) == 1
        assert "## Final answer" in files[0].read_text(encoding="utf-8")


async def test_f5_f6_without_result(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        rec = NotifyRecorder(app)
        await wait_tree(pilot)
        await pilot.press("f5")
        await pilot.press("f6")
        await pilot.press("f3")
        await pilot.pause()
        assert rec.messages.count("Nothing to copy/save yet") == 3
        assert not (root / "agora-runs").exists()


async def test_f5_copies_final(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        rec = NotifyRecorder(app)
        await run_prompt(pilot, "Q")
        await pilot.press("f5")
        await pilot.pause()
        assert app.clipboard == "Answer"
        assert "Copied" in rec.messages


async def test_f9_changes_generator_temperature(tmp_path: Path) -> None:
    calls: list[AppConfig] = []
    repo_yaml = Path(__file__).resolve().parents[2] / "config" / "agora.yaml"
    mtime = repo_yaml.stat().st_mtime
    app = AgoraApp(AppConfig(), root=make_project(tmp_path), service_factory=factory(calls=calls))
    async with app.run_test(size=(100, 40)) as pilot:
        await wait_tree(pilot)
        await pilot.press("f9")
        await pilot.pause()
        assert isinstance(app.screen, ModelsScreen)
        app.screen.query_one("#gen-temp", Input).value = "0.5"
        await pilot.click("#apply")
        await pilot.pause()
        assert not isinstance(app.screen, ModelsScreen)
        assert app.config.reflection.generator.temperature == 0.5
        assert len(calls) == 2
        assert "t=0.5" in str(app.query_one("#status").render())
    assert repo_yaml.stat().st_mtime == mtime


async def test_f9_invalid_temperature_keeps_dialog(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 40)) as pilot:
        await wait_tree(pilot)
        await pilot.press("f9")
        await pilot.pause()
        app.screen.query_one("#gen-temp", Input).value = "5"
        await pilot.click("#apply")
        await pilot.pause()
        assert isinstance(app.screen, ModelsScreen)
        assert "temperature" in str(app.screen.query_one("#models-error").render())
        assert app.config.reflection.generator.temperature == 0.9


async def test_f9_missing_api_key_keeps_old_service(tmp_path: Path) -> None:
    from ibikus.appa.agora.config import ConfigError

    def failing(cfg: AppConfig):  # type: ignore[no-untyped-def]
        if cfg.reflection.critic.provider == "openai":
            raise ConfigError("OPENAI_API_KEY is not set")
        return factory()(cfg)

    app = AgoraApp(AppConfig(), root=make_project(tmp_path), service_factory=failing)
    async with app.run_test(size=(100, 40)) as pilot:
        rec = NotifyRecorder(app)
        await wait_tree(pilot)
        await pilot.press("f9")
        await pilot.pause()
        app.screen.query_one("#critic-provider").value = "openai"  # type: ignore[attr-defined]
        await pilot.click("#apply")
        await pilot.pause()
        assert app.config.reflection.critic.provider == "anthropic"
        assert any("OPENAI_API_KEY" in m for m in rec.messages)


async def test_f1_f3_f4_open_screens(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        await run_prompt(pilot, "Q")
        for key, screen in (("f1", HelpScreen), ("f3", ViewerScreen), ("f4", ConfigScreen)):
            await pilot.press(key)
            await pilot.pause()
            assert isinstance(app.screen, screen), key
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, screen), key


async def test_run_key_ignored_while_dialog_open(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_tree(pilot)
        app.query_one("#prompt").insert("Q")  # type: ignore[attr-defined]
        await pilot.press("f1")
        await pilot.press("f2")
        await pilot.pause()
        assert app.last_result is None and not app.run_in_progress
