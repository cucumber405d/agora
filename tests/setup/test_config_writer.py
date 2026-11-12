import os
from pathlib import Path

import pytest
import yaml

from ibikus.appa.agora.config import load_config
from ibikus.appa.agora.setup import config_writer as w
from ibikus.appa.agora.setup.presets import load_presets


def _quality():  # type: ignore[no-untyped-def]
    return next(p for p in load_presets() if p.id == "quality")


def test_build_from_scratch_is_valid(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    w.write_config(w.build_config_data(_quality()), path)
    cfg = load_config(path, env={}, cwd=tmp_path)
    gen, crit = cfg.reflection.generator, cfg.reflection.critic
    assert (gen.provider, gen.name, gen.temperature, gen.think) == (
        "ollama",
        "qwen3.5:9b",
        0.9,
        False,
    )
    assert (crit.provider, crit.name, crit.temperature, crit.think) == (
        "ollama",
        "qwen3:14b",
        0.1,
        False,
    )
    assert crit.base_url == "http://localhost:11434/v1"
    assert cfg.reflection.language == "auto"
    assert cfg.context.max_total_tokens == 4500


def test_build_keeps_unrelated_keys() -> None:
    existing = {
        "observability": {"langfuse": {"enabled": "off"}},
        "reflection": {"max_iterations": 5, "prompts": {"critic": "x.md"}},
        "context": {"max_file_kb": 512},
    }
    data = w.build_config_data(_quality(), existing)
    assert data["observability"] == {"langfuse": {"enabled": "off"}}
    assert data["reflection"]["max_iterations"] == 5
    assert data["reflection"]["prompts"] == {"critic": "x.md"}
    assert data["context"] == {"max_file_kb": 512, "max_total_tokens": 4500}
    assert existing["context"] == {"max_file_kb": 512}  # input not mutated


def test_write_creates_bak(tmp_path: Path) -> None:
    path = tmp_path / "home" / "config.yaml"
    assert w.write_config({"a": 1}, path) is None
    bak = w.write_config({"a": 2}, path)
    assert bak == tmp_path / "home" / "config.yaml.bak"
    assert yaml.safe_load(bak.read_text(encoding="utf-8")) == {"a": 1}
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == {"a": 2}


def test_write_atomic_on_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config.yaml"
    w.write_config({"a": 1}, path)

    def fail(src: object, dst: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        w.write_config({"a": 2}, path)
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == {"a": 1}
    assert not (tmp_path / "config.yaml.tmp").exists()


def test_read_existing(tmp_path: Path) -> None:
    assert w.read_existing(tmp_path / "missing.yaml") is None
    (tmp_path / "c.yaml").write_text("reflection: {max_iterations: 4}\n", encoding="utf-8")
    assert w.read_existing(tmp_path / "c.yaml") == {"reflection": {"max_iterations": 4}}
    (tmp_path / "bad.yaml").write_text(": : :\n- [", encoding="utf-8")
    assert w.read_existing(tmp_path / "bad.yaml") is None


def test_build_tolerates_null_sections() -> None:
    data = w.build_config_data(_quality(), {"reflection": None, "context": None})
    assert data["reflection"]["critic"]["name"] == "qwen3:14b"
    assert data["context"] == {"max_total_tokens": 4500}
