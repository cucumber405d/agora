"""`agora doctor`: print the diagnostics without the TUI."""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Any, TextIO

from .diagnostics import Status, SystemReport, collect
from .presets import Preset, recommend, unmet

_UNICODE = {"ok": "✓", "warn": "⚠", "error": "✕"}
_ASCII = {"ok": "[ok]", "warn": "[!]", "error": "[x]"}
_EXIT: dict[Status, int] = {"ok": 0, "warn": 1, "error": 2}


def supports_unicode(out: TextIO) -> bool:
    encoding = (getattr(out, "encoding", None) or "").lower().replace("-", "")
    return encoding in {"utf8", "utf16", "utf32"}


def format_report(
    report: SystemReport,
    presets: Sequence[Preset],
    unicode: bool = True,
    config_path: Path | None = None,
) -> str:
    marks = _UNICODE if unicode else _ASCII
    lines = [f"{marks[c.status]} {c.name}: {c.detail}" for c in report.checks]
    lines.append(f"Config: {config_path}" if config_path else "Config: none yet, run `agora setup`")
    lines.append("")
    lines.append("Configurations:")
    best = recommend(presets, report)
    for p in presets:
        tag = " (recommended)" if best is not None and p.id == best.id else ""
        missing = unmet(p, report)
        why = f" - {'; '.join(missing)}" if missing else ""
        lines.append(f"  {p.title:<9} {p.generator} / {p.critic}, ~{p.download_gb:g} GB{tag}{why}")
    return "\n".join(lines)


async def doctor(
    network: bool = True,
    out: TextIO | None = None,
    collect: Callable[..., Awaitable[SystemReport]] = collect,
    presets: Sequence[Preset] | None = None,
    config_path: Path | None = None,
    **collect_kwargs: Any,
) -> int:
    """Print the report; exit code 0 = all ok, 1 = warnings, 2 = errors."""
    from .presets import load_presets

    out = out or sys.stdout
    report = await collect(network=network, **collect_kwargs)
    text = format_report(
        report, presets or load_presets(), supports_unicode(out), config_path=config_path
    )
    print(text, file=out)
    return _EXIT[report.worst]
