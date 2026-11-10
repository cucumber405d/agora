from datetime import datetime

from ibikus.appa.agora.reflection.events import IterationRecord, RunResult
from ibikus.appa.agora.reflection.export import render_run_markdown

from .fakes import c


def test_render_run_markdown() -> None:
    result = RunResult(
        final="Answer B",
        status="approved",
        iterations=2,
        best_score=9,
        history=[
            IterationRecord(iteration=1, draft="Answer A", critique=c(5, issues=["too short"])),
            IterationRecord(iteration=2, draft="Answer B", critique=c(9, approved=True)),
        ],
    )
    md = render_run_markdown("Q", result, datetime(2026, 11, 9, 12, 30))
    assert md.startswith("# Agora run 2026-11-09 12:30")
    assert "## Prompt\n\nQ" in md
    assert "## Final answer (approved, score 9)\n\nAnswer B" in md
    assert "### Iteration 1 — score 5" in md
    assert "- too short" in md
    assert "Overall fine." in md  # critic feedback
    assert md.index("### Iteration 1") < md.index("### Iteration 2")
