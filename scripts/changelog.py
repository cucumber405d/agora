"""Build CHANGELOG.md for a release from the EN parts of docs/impacts/*.md.

Usage: python scripts/changelog.py --version 0.2.0 [--since 2026-11-12] [--out CHANGELOG.md]
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def extract_en(markdown: str) -> str:
    """The body of the `## EN` section, up to the next `## ` heading."""
    match = re.search(r"^## EN\s*\n(.*?)(?=^## |\Z)", markdown, flags=re.M | re.S)
    return match.group(1).strip() if match else ""


def _title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def build_changelog(impacts_dir: Path, since: date | None, version: str) -> str:
    entries = []
    for path in sorted(impacts_dir.glob("*.md")):
        m = _DATE.match(path.name)
        if m is None:
            continue
        if since is not None and date.fromisoformat(m.group(1)) < since:
            continue
        text = path.read_text(encoding="utf-8")
        body = extract_en(text)
        if body:
            entries.append(f"### {_title(text, path.stem)}\n\n{body}")
    return f"## {version}\n\n" + "\n\n".join(entries) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--since", type=date.fromisoformat)
    parser.add_argument("--impacts", type=Path, default=Path("docs/impacts"))
    parser.add_argument("--out", type=Path, default=Path("CHANGELOG.md"))
    args = parser.parse_args(argv)
    args.out.write_text(build_changelog(args.impacts, args.since, args.version), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
