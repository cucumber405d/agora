"""Load local files into a Context, enforcing size, encoding and token limits."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from ibikus.appa.agora.config import ContextConfig

from .models import Context, ContextFile, SkippedFile, SkipReason, estimate_tokens


class ContextSource(Protocol):
    def load(self, paths: Sequence[Path]) -> Context: ...


class FileContextSource:
    """Reads files in the given order; the token budget is applied cumulatively."""

    def __init__(self, cfg: ContextConfig, root: Path) -> None:
        self._cfg = cfg
        self._root = root.resolve()
        self._allowed = {ext.lower() for ext in cfg.allowed_ext}

    def _display(self, path: Path) -> Path:
        resolved = path.resolve()
        try:
            return resolved.relative_to(self._root)
        except ValueError:
            return resolved

    def _read(self, path: Path) -> tuple[str | None, SkipReason | None]:
        """Return (text, None) on success or (None, reason) when the file is skipped."""
        if path.suffix.lower() not in self._allowed:
            return None, "extension"
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

    def load(self, paths: Sequence[Path]) -> Context:
        ctx = Context()
        used = 0
        for path in paths:
            shown = self._display(path)
            text, reason = self._read(path)
            if text is None:
                ctx.skipped.append(SkippedFile(path=shown, reason=reason or "unreadable"))
                continue
            tokens = estimate_tokens(text)
            if used + tokens > self._cfg.max_total_tokens:
                ctx.skipped.append(SkippedFile(path=shown, reason="over_budget"))
                continue
            used += tokens
            ctx.files.append(ContextFile(path=shown, content=text, tokens=tokens))
        return ctx
