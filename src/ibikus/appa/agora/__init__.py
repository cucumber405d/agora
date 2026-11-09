"""Agora - reflection agent with a Far-style console UI."""

import os

# Pydantic AI 2.x prints a banner to stdout on first run, which corrupts the TUI.
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

__version__ = "0.1.0"
