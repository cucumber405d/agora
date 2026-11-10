from pathlib import Path

import pytest
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
        assert "Copied 6 characters" in rec.messages


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


async def test_f9_provider_switch_drops_base_url(tmp_path: Path) -> None:
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 40)) as pilot:
        await wait_tree(pilot)
        await pilot.press("f9")
        await pilot.pause()
        app.screen.query_one("#gen-provider").value = "openai"  # type: ignore[attr-defined]
        app.screen.query_one("#gen-name", Input).value = "gpt-4o-mini"
        await pilot.click("#apply")
        await pilot.pause()
        gen = app.config.reflection.generator
        assert (gen.provider, gen.name, gen.base_url) == ("openai", "gpt-4o-mini", None)


async def test_f6_after_failed_run_does_not_save_stale_answer(tmp_path: Path) -> None:
    from pydantic_ai.exceptions import ModelConnectionError

    root = make_project(tmp_path)
    app = make_app(root, drafts=["Answer", ModelConnectionError("m", "refused")])
    async with app.run_test(size=(100, 30)) as pilot:
        rec = NotifyRecorder(app)
        await run_prompt(pilot, "Q1")
        assert app.last_result is not None
        app.query_one("#prompt").clear()  # type: ignore[attr-defined]
        await run_prompt(pilot, "Q2")
        await pilot.press("f6")
        await pilot.pause()
        assert "Nothing to copy/save yet" in rec.messages
        assert not (root / "agora-runs").exists()


async def test_f6_write_error_notifies_instead_of_crash(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    (root / "agora-runs").write_text("not a directory", encoding="utf-8")
    app = make_app(root)
    async with app.run_test(size=(100, 30)) as pilot:
        rec = NotifyRecorder(app)
        await run_prompt(pilot, "Q")
        await pilot.press("f6")
        await pilot.pause()
        assert any(m.startswith("Cannot save:") for m in rec.messages)
        assert app.return_code is None


async def test_ctrl_c_in_log_entry_uses_system_clipboard(
    tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
) -> None:
    import pyperclip

    from ibikus.appa.agora.reflection.events import LlmExchange
    from ibikus.appa.agora.tui.dialogs import LogEntryScreen

    copied: list[str] = []
    monkeypatch.setattr(pyperclip, "copy", copied.append)
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        rec = NotifyRecorder(app)
        await wait_tree(pilot)
        entry = LlmExchange(role="critic", direction="request", model="m", text="привет\nмир")
        app.push_screen(LogEntryScreen(entry))
        await pilot.pause()
        await pilot.press("f7", "ctrl+c")
        await pilot.pause()
        assert copied == ["привет\nмир"]
        assert "Copied 10 characters" in rec.messages


async def test_copy_survives_missing_system_clipboard(
    tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
) -> None:
    import pyperclip

    def broken(text: str) -> None:
        raise pyperclip.PyperclipException("no clipboard")

    monkeypatch.setattr(pyperclip, "copy", broken)
    app = make_app(make_project(tmp_path))
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_tree(pilot)
        app.copy_to_clipboard("x")  # must not raise; OSC 52 path still used
        assert app.clipboard == "x"
