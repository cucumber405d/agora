from pathlib import Path

import ibikus.appa.agora as agora

ROOT = Path(__file__).parent.parent


def test_version_is_0_2_0() -> None:
    assert agora.__version__ == "0.2.0"


def test_iss_is_per_user() -> None:
    iss = (ROOT / "packaging" / "agora.iss").read_text(encoding="utf-8")
    assert "PrivilegesRequired=lowest" in iss
    assert r"{localappdata}\Programs\Agora" in iss
    assert "OutputBaseFilename=Agora-Setup-{#AppVersion}" in iss


def test_spec_bundles_resources() -> None:
    spec = (ROOT / "packaging" / "agora.spec").read_text(encoding="utf-8")
    for name in ("ibikus.appa.agora", "markitdown", "magika", "pdfminer"):
        assert name in spec


def test_launcher_prefers_windows_terminal() -> None:
    cmd = (ROOT / "packaging" / "launch.cmd").read_text(encoding="utf-8")
    assert "where wt" in cmd
    assert "chcp 65001" in cmd
