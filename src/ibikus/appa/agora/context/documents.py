"""Convert office documents and HTML to Markdown (markitdown) with a cache and a timeout."""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path

logger = logging.getLogger(__name__)

DOCUMENT_FORMATS: dict[str, str] = {
    ".pdf": "PDF",
    ".docx": "DOCX",
    ".pptx": "PPTX",
    ".xlsx": "XLSX",
    ".html": "HTML",
    ".htm": "HTML",
}
LEGACY_EXT = frozenset({".doc", ".xls", ".ppt"})


class ConversionError(Exception):
    """The document could not be converted (broken file, unsupported content, timeout)."""


def _markitdown(path: Path) -> str:
    from markitdown import MarkItDown  # heavy import, only when a document is converted

    return MarkItDown().convert(str(path)).text_content


class DocumentConverter:
    """Thread-safe enough for one UI: conversions are cached by (path, mtime, size)."""

    def __init__(self, timeout_s: float = 60, convert: Callable[[Path], str] | None = None) -> None:
        self._timeout_s = timeout_s
        self._convert = convert or _markitdown
        self._cache: dict[tuple[str, int, int], str] = {}

    def to_markdown(self, path: Path) -> str:
        resolved = path.resolve()
        st = resolved.stat()
        key = (str(resolved), st.st_mtime_ns, st.st_size)
        if key in self._cache:
            return self._cache[key]
        pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="agora-convert")
        try:
            future = pool.submit(self._convert, resolved)
            text = future.result(timeout=self._timeout_s)
        except FutureTimeout as e:
            raise ConversionError("timeout") from e
        except Exception as e:
            raise ConversionError(f"{type(e).__name__}: {e}") from e
        finally:
            pool.shutdown(wait=False)  # a hung conversion must not block the caller
        self._cache[key] = text
        return text
