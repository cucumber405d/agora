from pathlib import Path

from ibikus.appa.agora.config import ContextConfig
from ibikus.appa.agora.context import Context, FileContextSource, estimate_tokens


def _src(root: Path, **kw: object) -> FileContextSource:
    return FileContextSource(ContextConfig.model_validate(kw), root)


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello") == 2
    assert estimate_tokens("abcd") == 1


def test_loads_allowed_files_relative_to_root(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("hello", encoding="utf-8")
    ctx = _src(tmp_path).load([tmp_path / "a.md"])
    assert [(f.path, f.content, f.tokens) for f in ctx.files] == [(Path("a.md"), "hello", 2)]
    assert ctx.total_tokens == 2
    assert ctx.skipped == []


def test_skips_disallowed_extension(tmp_path: Path) -> None:
    (tmp_path / "x.exe").write_bytes(b"MZ")
    ctx = _src(tmp_path).load([tmp_path / "x.exe"])
    assert ctx.files == []
    assert [(s.path, s.reason) for s in ctx.skipped] == [(Path("x.exe"), "extension")]


def test_extension_match_is_case_insensitive(tmp_path: Path) -> None:
    (tmp_path / "README.MD").write_text("x", encoding="utf-8")
    assert len(_src(tmp_path).load([tmp_path / "README.MD"]).files) == 1


def test_skips_too_large(tmp_path: Path) -> None:
    (tmp_path / "big.txt").write_text("x" * 2048, encoding="utf-8")
    ctx = _src(tmp_path, max_file_kb=1).load([tmp_path / "big.txt"])
    assert [s.reason for s in ctx.skipped] == ["too_large"]


def test_skips_non_utf8(tmp_path: Path) -> None:
    (tmp_path / "b.json").write_bytes("привет".encode("cp1251"))
    ctx = _src(tmp_path).load([tmp_path / "b.json"])
    assert [s.reason for s in ctx.skipped] == ["not_utf8"]


def test_skips_binary_with_nul(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_bytes(b"\x00\x01")
    assert [s.reason for s in _src(tmp_path).load([tmp_path / "b.txt"]).skipped] == ["not_utf8"]


def test_budget_is_cumulative_and_ordered(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("hello", encoding="utf-8")
    (tmp_path / "b.md").write_text("world", encoding="utf-8")
    ctx = _src(tmp_path, max_total_tokens=3).load([tmp_path / "a.md", tmp_path / "b.md"])
    assert [f.path for f in ctx.files] == [Path("a.md")]
    assert [(s.path, s.reason) for s in ctx.skipped] == [(Path("b.md"), "over_budget")]


def test_missing_file_is_unreadable(tmp_path: Path) -> None:
    ctx = _src(tmp_path).load([tmp_path / "gone.md"])
    assert [s.reason for s in ctx.skipped] == ["unreadable"]


def test_path_outside_root_kept_absolute(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / "out.md").write_text("x", encoding="utf-8")
    ctx = _src(root).load([tmp_path / "out.md"])
    assert ctx.files[0].path == tmp_path / "out.md"


def test_empty_context() -> None:
    assert Context.empty().total_tokens == 0
