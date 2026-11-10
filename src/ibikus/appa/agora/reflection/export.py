"""Markdown export of a finished run (final answer plus iteration history)."""

from __future__ import annotations

from datetime import datetime

from .events import RunResult


def render_run_markdown(prompt: str, result: RunResult, created: datetime) -> str:
    lines = [
        f"# Agora run {created:%Y-%m-%d %H:%M}",
        "",
        "## Prompt",
        "",
        prompt,
        "",
        f"## Final answer ({result.status}, score {result.best_score})",
        "",
        result.final,
        "",
        "## Iterations",
    ]
    for rec in result.history:
        c = rec.critique
        lines += ["", f"### Iteration {rec.iteration} — score {c.score}", "", rec.draft, ""]
        lines += [f"**Critic:** {c.feedback}", ""]
        lines += ["**Issues:**", ""] + ([f"- {i}" for i in c.issues] or ["- (none)"])
        if c.suggestions:
            lines += ["", "**Suggestions:**", "", *[f"- {s}" for s in c.suggestions]]
    return "\n".join(lines) + "\n"
