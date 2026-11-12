import io

import pytest

from ibikus.appa.agora.setup import cli
from ibikus.appa.agora.setup.diagnostics import Check, Gpu, OllamaInfo, SystemReport
from ibikus.appa.agora.setup.presets import load_presets


def _report(*statuses: str, gpu: Gpu | None = None) -> SystemReport:
    checks = tuple(Check(f"C{i}", s, "detail") for i, s in enumerate(statuses))  # type: ignore[arg-type]
    return SystemReport("Windows 11", 32, 100, gpu, OllamaInfo(True, True), checks)


@pytest.mark.parametrize(
    ("statuses", "code"), [(("ok", "ok"), 0), (("ok", "warn"), 1), (("warn", "error"), 2)]
)
async def test_doctor_exit_codes(statuses: tuple[str, ...], code: int) -> None:
    async def collect(**_: object) -> SystemReport:
        return _report(*statuses)

    out = io.StringIO()
    assert await cli.doctor(out=out, collect=collect) == code


def test_format_report_marks_recommended() -> None:
    text = cli.format_report(_report("ok", gpu=Gpu("RTX 4070", 12)), load_presets(), unicode=True)
    line = next(row for row in text.splitlines() if "Quality" in row)
    assert "(recommended)" in line
    assert "✓ C0: detail" in text


def test_format_report_ascii_fallback() -> None:
    text = cli.format_report(_report("ok", "warn", "error"), load_presets(), unicode=False)
    assert "[ok] C0" in text and "[!] C1" in text and "[x] C2" in text
    assert "✓" not in text


def test_format_report_lists_unmet() -> None:
    text = cli.format_report(_report("ok"), load_presets(), unicode=True)
    assert "needs 12 GB VRAM" in text


def test_supports_unicode() -> None:
    class Out(io.StringIO):
        def __init__(self, encoding: str) -> None:
            super().__init__()
            self._enc = encoding

        @property
        def encoding(self) -> str:  # type: ignore[override]
            return self._enc

    assert cli.supports_unicode(Out("utf-8"))
    assert not cli.supports_unicode(Out("cp1252"))
