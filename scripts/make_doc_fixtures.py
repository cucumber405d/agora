"""Generate the small document fixtures under tests/fixtures/docs (run once, commit output)."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import openpyxl
from docx import Document
from pptx import Presentation
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

TEXT = "Agora sample document"


def _pdf(path: Path, text: str | None) -> None:
    c = canvas.Canvas(str(path), invariant=True)
    if text is not None:
        c.drawString(72, 720, text)
    else:
        # A tiny grey image only: a "scan" with no text layer.
        from PIL import Image

        buf = io.BytesIO()
        Image.new("L", (40, 20), 128).save(buf, format="PNG")
        c.drawImage(ImageReader(io.BytesIO(buf.getvalue())), 72, 600, 200, 100)
    c.showPage()
    c.save()


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    _pdf(out / "sample.pdf", f"{TEXT} PDF")
    _pdf(out / "scan.pdf", None)
    (out / "broken.pdf").write_bytes((out / "sample.pdf").read_bytes()[:200])

    doc = Document()
    doc.add_paragraph(f"{TEXT} DOCX")
    doc.save(str(out / "sample.docx"))

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = f"{TEXT} PPTX"
    prs.save(str(out / "sample.pptx"))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = f"{TEXT} XLSX"
    wb.save(str(out / "sample.xlsx"))

    (out / "sample.html").write_text(
        f"<html><body><h1>{TEXT} HTML</h1></body></html>", encoding="utf-8"
    )
    (out / "old.doc").write_bytes(b"\xd0\xcf\x11\xe0legacy word file")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures/docs"))
