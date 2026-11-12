from pathlib import Path

from ibikus.appa.agora import paths


def test_agora_home_respects_env(tmp_path: Path) -> None:
    assert paths.agora_home({"AGORA_HOME": str(tmp_path)}) == tmp_path


def test_agora_home_default_ends_with_dot_agora(monkeypatch: object) -> None:
    assert paths._real_default_home().name == ".agora"


def test_user_files_live_in_home(tmp_path: Path) -> None:
    env = {"AGORA_HOME": str(tmp_path)}
    assert paths.user_config_path(env) == tmp_path / "config.yaml"
    assert paths.downloads_dir(env) == tmp_path / "downloads"


def test_is_frozen_false_in_tests() -> None:
    assert paths.is_frozen() is False
