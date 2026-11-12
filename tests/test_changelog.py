import importlib.util
import sys
from datetime import date
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "changelog", Path(__file__).parent.parent / "scripts" / "changelog.py"
)
assert _spec is not None and _spec.loader is not None
changelog = importlib.util.module_from_spec(_spec)
sys.modules["changelog"] = changelog
_spec.loader.exec_module(changelog)

IMPACT = """# 2026-11-12 — Thing

## RU
- **Что изменилось:** по-русски

## EN
- **What changed:** in English
- **Why:** because
"""


def test_extract_en() -> None:
    assert changelog.extract_en(IMPACT) == "- **What changed:** in English\n- **Why:** because"


def test_extract_en_missing_returns_empty() -> None:
    assert changelog.extract_en("# x\n\n## RU\ntext\n") == ""


def test_build_changelog_since_filters_and_orders(tmp_path: Path) -> None:
    for day, title in (("09", "Old"), ("12", "Newest"), ("10", "Middle")):
        (tmp_path / f"2026-11-{day}-x{day}.md").write_text(
            IMPACT.replace("Thing", title), encoding="utf-8"
        )
    text = changelog.build_changelog(tmp_path, date(2026, 11, 10), "0.2.0")
    assert text.startswith("## 0.2.0\n")
    assert "Old" not in text
    assert text.index("Middle") < text.index("Newest")
    assert "in English" in text and "по-русски" not in text


def test_build_changelog_without_since_takes_all(tmp_path: Path) -> None:
    (tmp_path / "2026-11-09-a.md").write_text(IMPACT, encoding="utf-8")
    assert "### 2026-11-12 — Thing" in changelog.build_changelog(tmp_path, None, "0.2.0")
