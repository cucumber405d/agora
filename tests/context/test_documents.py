import shutil
import time
from pathlib import Path

import pytest

from ibikus.appa.agora.context.documents import ConversionError, DocumentConverter

DOCS = Path(__file__).parent.parent / "fixtures" / "docs"


@pytest.mark.parametrize(
    ("name", "marker"),
    [
        ("sample.pdf", "PDF"),
        ("sample.docx", "DOCX"),
        ("sample.pptx", "PPTX"),
        ("sample.xlsx", "XLSX"),
        ("sample.html", "HTML"),
    ],
)
def test_converts_each_format(name: str, marker: str) -> None:
    text = DocumentConverter().to_markdown(DOCS / name)
    assert f"Agora sample document {marker}" in text


def test_cache_hit_skips_second_convert(tmp_path: Path) -> None:
    calls: list[Path] = []
    conv = DocumentConverter(convert=lambda p: calls.append(p) or "text")
    f = tmp_path / "a.pdf"
    f.write_bytes(b"x")
    assert conv.to_markdown(f) == "text"
    assert conv.to_markdown(f) == "text"
    assert len(calls) == 1


def test_cache_invalidated_on_change(tmp_path: Path) -> None:
    calls: list[Path] = []
    conv = DocumentConverter(convert=lambda p: calls.append(p) or f"v{len(calls)}")
    f = tmp_path / "a.pdf"
    f.write_bytes(b"x")
    assert conv.to_markdown(f) == "v1"
    f.write_bytes(b"xyz")
    assert conv.to_markdown(f) == "v2"


def test_timeout_raises(tmp_path: Path) -> None:
    def slow(_: Path) -> str:
        time.sleep(1)
        return "late"

    f = tmp_path / "a.pdf"
    f.write_bytes(b"x")
    with pytest.raises(ConversionError, match="timeout"):
        DocumentConverter(timeout_s=0.1, convert=slow).to_markdown(f)


def test_broken_pdf_raises_conversion_error() -> None:
    with pytest.raises(ConversionError):
        DocumentConverter().to_markdown(DOCS / "broken.pdf")


def test_unicode_path(tmp_path: Path) -> None:
    target = tmp_path / "Мои документы" / "отчёт.pdf"
    target.parent.mkdir()
    shutil.copy(DOCS / "sample.pdf", target)
    assert "Agora sample document PDF" in DocumentConverter().to_markdown(target)
