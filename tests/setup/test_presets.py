import pytest

from ibikus.appa.agora.setup.diagnostics import Gpu, OllamaInfo, SystemReport
from ibikus.appa.agora.setup.presets import (
    default_choice,
    disk_shortfall_gb,
    load_presets,
    recommend,
    unmet,
)


def report(ram: float, gpu: Gpu | None, free: float = 100) -> SystemReport:
    return SystemReport("Windows 11", ram, free, gpu, OllamaInfo(True, True), ())


def by_id(pid: str):  # type: ignore[no-untyped-def]
    return next(p for p in load_presets() if p.id == pid)


def test_presets_from_spec() -> None:
    presets = load_presets()
    assert [p.id for p in presets] == ["light", "standard", "quality"]
    q = by_id("quality")
    assert (q.generator, q.critic, q.ollama_context, q.max_total_tokens) == (
        "qwen3.5:9b",
        "qwen3:14b",
        8192,
        4500,
    )
    assert by_id("light").ollama_context == 4096
    assert by_id("light").max_total_tokens == 2500


@pytest.mark.parametrize(
    ("ram", "gpu", "expected"),
    [
        (16, None, "light"),
        (16, Gpu("RTX 3060 Ti", 8), "standard"),
        (32, Gpu("RTX 4070", 12), "quality"),
        (32, Gpu("Intel UHD", None), "light"),
        (4, None, None),
    ],
)
def test_recommend(ram: float, gpu: Gpu | None, expected: str | None) -> None:
    rec = recommend(load_presets(), report(ram, gpu))
    assert (rec.id if rec else None) == expected


def test_unknown_vram_is_reported() -> None:
    assert "GPU memory unknown" in unmet(by_id("standard"), report(32, Gpu("Intel UHD", None)))
    assert any("12 GB VRAM" in r for r in unmet(by_id("quality"), report(32, Gpu("x", 8))))
    assert any("8 GB RAM" in r for r in unmet(by_id("light"), report(4, None)))


def test_default_choice_falls_back_to_light() -> None:
    assert default_choice(load_presets(), report(4, None)).id == "light"


def test_disk_shortfall() -> None:
    assert disk_shortfall_gb(by_id("quality"), report(32, None, free=10)) == pytest.approx(7.0)
    assert disk_shortfall_gb(by_id("light"), report(32, None, free=10)) == 0
