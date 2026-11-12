"""Load local files into a Context, enforcing size, encoding and token limits."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from ibikus.appa.agora.config import ContextConfig

from .documents import DOCUMENT_FORMATS, LEGACY_EXT, ConversionError, DocumentConverter
from .models import Context, ContextFile, SkippedFile, SkipReason, estimate_tokens

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]


class ContextSource(Protocol):
    def load(self, paths: Sequence[Path]) -> Context: ...


class FileContextSource:
    """Reads files in the given order; the token budget is applied cumulatively.
    Documents (PDF, DOCX, ...) are converted to Markdown first."""

    def __init__(
        self, cfg: ContextConfig, root: Path, converter: DocumentConverter | None = None
    ) -> None:
        self._cfg = cfg
        self._root = root.resolve()
        self._allowed = {ext.lower() for ext in cfg.allowed_ext}
        self._converter = converter or DocumentConverter(timeout_s=cfg.convert_timeout_s)

    def _display(self, path: Path) -> Path:
        resolved = path.resolve()
        try:
            return resolved.relative_to(self._root)
        except ValueError:
            return resolved

    def _read_document(self, path: Path) -> tuple[str | None, SkipReason | None]:
        try:
            if path.stat().st_size > self._cfg.max_document_mb * 1024 * 1024:
                return None, "too_large"
            text = self._converter.to_markdown(path)
        except OSError:
            return None, "unreadable"
        except ConversionError:
            logger.warning("Cannot convert %s", path, exc_info=True)
            return None, "convert_failed"
        if not text.strip():
            return None, "no_text"
        return text, None

    def _read_text(self, path: Path) -> tuple[str | None, SkipReason | None]:
        try:
            if path.stat().st_size > self._cfg.max_file_kb * 1024:
                return None, "too_large"
            data = path.read_bytes()
        except OSError:
            return None, "unreadable"
        if b"\x00" in data:
            return None, "not_utf8"
        try:
            return data.decode("utf-8"), None
        except UnicodeDecodeError:
            return None, "not_utf8"

    def _read(self, path: Path) -> tuple[str | None, SkipReason | None]:
        """Return (text, None) on success or (None, reason) when the file is skipped."""
        ext = path.suffix.lower()
        if ext in LEGACY_EXT:
            return None, "legacy_format"
        if ext in DOCUMENT_FORMATS:  # always allowed: older configs list only text types
            return self._read_document(path)
        if ext not in self._allowed:
            return None, "extension"
        return self._read_text(path)

    def load(self, paths: Sequence[Path], on_progress: ProgressCallback | None = None) -> Context:
        ctx = Context()
        used = 0
        documents = [p for p in paths if p.suffix.lower() in DOCUMENT_FORMATS]
        converted = 0
        for path in paths:
            shown = self._display(path)
            text, reason = self._read(path)
            fmt = DOCUMENT_FORMATS.get(path.suffix.lower())
            if fmt is not None:
                converted += 1
                if on_progress is not None:
                    on_progress(converted, len(documents))
            if text is None:
                ctx.skipped.append(SkippedFile(path=shown, reason=reason or "unreadable"))
                continue
            tokens = estimate_tokens(text)
            if used + tokens > self._cfg.max_total_tokens:
                ctx.skipped.append(SkippedFile(path=shown, reason="over_budget"))
                continue
            used += tokens
            ctx.files.append(
                ContextFile(path=shown, content=text, tokens=tokens, source_format=fmt)
            )
        return ctx
