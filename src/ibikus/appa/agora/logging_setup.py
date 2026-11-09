"""File-only logging: nothing may reach stdout/stderr while the TUI owns the terminal."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_MARK = "_agora_handler"


def setup_logging(home: Path) -> Path:
    """Route all logging (and Python warnings) to <home>/logs/agora.log. Returns the path."""
    log_dir = home / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "agora.log"
    root = logging.getLogger()
    for h in [h for h in root.handlers if getattr(h, _MARK, False)]:
        root.removeHandler(h)
        h.close()
    handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    setattr(handler, _MARK, True)
    root.addHandler(handler)
    root.setLevel(os.environ.get("AGORA_LOG_LEVEL", "INFO").upper())
    logging.captureWarnings(False)  # re-install even if a previous call was undone
    logging.captureWarnings(True)
    return path
