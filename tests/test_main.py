import logging
import os
import warnings
from pathlib import Path

import pytest

from ibikus.appa.agora import __main__ as entry
from ibikus.appa.agora.logging_setup import setup_logging
from ibikus.appa.agora.tui.app import AgoraApp


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGORA_HOME", str(tmp_path / "home"))
    for key in ("ANTHROPIC_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(AgoraApp, "run", lambda self, *a, **k: None)


def _yaml(tmp_path: Path, text: str) -> str:
    p = tmp_path / "agora.yaml"
    p.write_text(text, encoding="utf-8")
    return str(p)


LOCAL_ONLY = """
reflection:
  critic: {provider: ollama, name: qwen2.5:7b, temperature: 0.1}
"""


def test_invalid_config_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = entry.main(["--config", _yaml(tmp_path, "reflection:\n  approve_threshold: 11\n")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "Invalid configuration" in err
    assert "reflection.approve_threshold" in err


def test_missing_api_key_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = entry.main(["--config", _yaml(tmp_path, "reflection: {}\n")])
    assert rc == 2
    assert "ANTHROPIC_API_KEY is not set" in capsys.readouterr().err


def test_happy_path_returns_0(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert entry.main(["--config", _yaml(tmp_path, LOCAL_ONLY)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""  # nothing may be printed around the TUI
    assert (tmp_path / "home" / "logs" / "agora.log").exists()


def test_dotenv_is_loaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=from-dotenv\n", encoding="utf-8")
    assert entry.main(["--config", _yaml(tmp_path, "reflection: {}\n")]) == 0
    assert os.environ["ANTHROPIC_API_KEY"] == "from-dotenv"


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        entry.main(["--version"])
    assert exc.value.code == 0
    assert "agora 0.2.0" in capsys.readouterr().out


def test_logging_goes_to_file_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = setup_logging(tmp_path / "h")
    logging.getLogger("x").warning("hi there")
    warnings.showwarning(UserWarning("py warning"), UserWarning, "f.py", 1)
    for h in logging.getLogger().handlers:
        h.flush()
    text = path.read_text(encoding="utf-8")
    assert "hi there" in text
    assert "py warning" in text
    assert capsys.readouterr().err == ""


def test_banner_env_set() -> None:
    import ibikus.appa.agora  # noqa: F401

    assert os.environ["PYDANTIC_AI_NO_BANNER"] == "1"


def test_missing_prompt_file_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = LOCAL_ONLY + "  prompts: {generator: nope.md}\n"
    assert entry.main(["--config", _yaml(tmp_path, cfg)]) == 2
    assert "reflection.prompts.generator" in capsys.readouterr().err


def test_main_doctor_no_network(capsys: pytest.CaptureFixture[str]) -> None:
    rc = entry.main(["doctor", "--no-network"])
    assert rc in (0, 1, 2)
    out = capsys.readouterr().out
    assert "OS" in out
    assert "Config" in out


def _capture_app(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    seen: list[dict[str, object]] = []
    original = AgoraApp.__init__

    def init(self: AgoraApp, *args: object, **kwargs: object) -> None:
        seen.append(kwargs)
        original(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(AgoraApp, "__init__", init)
    return seen


def test_main_first_run_starts_wizard(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _capture_app(monkeypatch)
    assert entry.main([]) == 0  # no config anywhere: must not fail on the cloud critic key
    assert seen[0]["start_wizard"] is True


def test_main_with_config_no_wizard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _capture_app(monkeypatch)
    assert entry.main(["--config", _yaml(tmp_path, LOCAL_ONLY)]) == 0
    assert seen[0]["start_wizard"] is False


def test_main_setup_forces_wizard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _capture_app(monkeypatch)
    assert entry.main(["--config", _yaml(tmp_path, LOCAL_ONLY), "setup"]) == 0
    assert seen[0]["start_wizard"] is True


def test_main_convert_prints_markdown(capsys: pytest.CaptureFixture[str]) -> None:
    sample = Path(__file__).parent / "fixtures" / "docs" / "sample.pdf"
    assert entry.main(["convert", str(sample)]) == 0
    assert "Agora sample document PDF" in capsys.readouterr().out


def test_main_convert_failure_exit_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    broken = Path(__file__).parent / "fixtures" / "docs" / "broken.pdf"
    assert entry.main(["convert", str(broken)]) == 1
    assert "Cannot convert" in capsys.readouterr().err
