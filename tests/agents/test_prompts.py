from pathlib import Path

from ibikus.appa.agora.agents.critic import Critique
from ibikus.appa.agora.agents.prompts import (
    build_critic_input,
    build_generator_input,
    load_instructions,
    render_context,
)
from ibikus.appa.agora.context import Context, ContextFile


def ctx_with(path: str, content: str) -> Context:
    return Context(files=[ContextFile(path=Path(path), content=content, tokens=1)])


def test_render_context_headers() -> None:
    out = render_context(ctx_with("docs/a.md", "x"))
    assert "### file: docs/a.md" in out
    assert "```\nx\n```" in out


def test_render_empty_context() -> None:
    assert render_context(Context.empty()) == ""


def test_generator_first_iteration_has_no_revision_sections() -> None:
    s = build_generator_input("Q", Context.empty())
    assert "## Request\nQ" in s
    assert "## Previous draft" not in s
    assert "## Context" not in s


def test_generator_context_before_request() -> None:
    s = build_generator_input("Q", ctx_with("a.md", "x"))
    assert s.index("## Context") < s.index("## Request")


def test_generator_revision_includes_draft_and_critique() -> None:
    crit = Critique(approved=False, score=5, issues=["too vague"], suggestions=["add example"])
    s = build_generator_input("Q", Context.empty(), "D1", crit)
    assert s.index("## Request") < s.index("## Previous draft") < s.index("## Critique")
    assert "D1" in s
    assert "score: 5" in s
    assert "- too vague" in s
    assert "- add example" in s
    assert "Revise the previous draft to address every issue in the critique." in s


def test_critic_input_order() -> None:
    s = build_critic_input("Q", ctx_with("a.md", "x"), "D")
    assert s.index("## Context") < s.index("## Request") < s.index("## Draft")


def test_override_instructions(tmp_path: Path) -> None:
    p = tmp_path / "c.md"
    p.write_text("custom", encoding="utf-8")
    assert load_instructions("critic", p) == "custom"


def test_builtin_instructions_non_empty() -> None:
    assert load_instructions("generator", None).strip()
    assert "score" in load_instructions("critic", None).lower()
