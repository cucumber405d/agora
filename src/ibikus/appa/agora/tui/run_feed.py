"""Run feed: one collapsible block per iteration with live draft and critique."""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import Collapsible, Static

from ibikus.appa.agora.reflection.events import (
    CritiqueDone,
    CritiqueFailed,
    DraftChunk,
    DraftDone,
    IterationStarted,
    RunEvent,
    RunFailed,
    RunFinished,
)


@dataclass
class _Iteration:
    box: Collapsible
    draft: Static
    critique: Static
    text: list[str] = field(default_factory=list)


class RunFeed(VerticalScroll):
    """Model output is always rendered as plain Text, never as Textual markup."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._iters: dict[int, _Iteration] = {}
        self._plain: list[str] = []
        self._max = 0
        self._scores: list[int] = []

    def clear(self) -> None:
        self.remove_children()
        self._iters.clear()
        self._plain.clear()
        self._scores.clear()
        self._max = 0
        self._update_title(None)

    def plain_text(self) -> str:
        parts = list(self._plain)
        for it in self._iters.values():
            parts.append("".join(it.text))
        return "\n".join(p for p in parts if p)

    def _update_title(self, iteration: int | None) -> None:
        title = "Run"
        if iteration is not None:
            title += f" ─ iter {iteration}/{self._max}"
        if self._scores:
            title += " ─ score " + " → ".join(str(s) for s in self._scores[-2:])
        self.border_title = title

    def _add(self, label: str, body: str, classes: str) -> None:
        self._plain.append(f"{label}\n{body}")
        self.mount(Static(Text(label, style="bold")), Static(Text(body), classes=classes))
        self.scroll_end(animate=False)

    def apply(self, event: RunEvent) -> None:
        match event:
            case IterationStarted(iteration=n, max_iterations=m):
                self._max = m
                for it in self._iters.values():
                    it.box.collapsed = True
                # Only the draft is collapsible; the critique below it always stays visible.
                draft, critique = Static(Text(""), classes="draft"), Static("", classes="critique")
                box = Collapsible(draft, title=f"Iter {n}", collapsed=False)
                self._iters[n] = _Iteration(box, draft, critique)
                self._plain.append(f"Iter {n}")
                self.mount(box, critique)
                self._update_title(n)
            case DraftChunk(iteration=n, text=t):
                it = self._iters[n]
                it.text.append(t)
                it.draft.update(Text("".join(it.text)))
            case DraftDone(iteration=n, text=t, truncated=cut):
                it = self._iters[n]
                it.text = [t]
                it.draft.update(Text(t))
                if cut:
                    warning = (
                        "⚠ draft truncated: the token/context limit was reached. "
                        "Raise OLLAMA_CONTEXT_LENGTH or mark fewer files."
                    )
                    self._plain.append(warning)
                    self.mount(Static(Text(warning), classes="warning"), before=it.critique)
            case CritiqueDone(iteration=n, critique=c):
                self._scores.append(c.score)
                lines = [f"critique: score {c.score}/10" + (" (approved)" if c.approved else "")]
                lines.append(c.feedback)
                if c.issues:
                    lines += ["Issues:", *[f"  - {i}" for i in c.issues]]
                if c.suggestions:
                    lines += ["Suggestions:", *[f"  - {s}" for s in c.suggestions]]
                body = "\n".join(lines)
                self._plain.append(body)
                self._iters[n].critique.update(Text(body, style="italic"))
                self._iters[n].box.title = f"Iter {n} ─ score {c.score}"
                self._update_title(n)
            case CritiqueFailed(iteration=n, message=msg):
                body = f"critique failed: {msg}"
                self._plain.append(body)
                self._iters[n].critique.update(Text(body))
                self._iters[n].critique.add_class("warning")
                self._iters[n].box.title = f"Iter {n} ─ not graded"
            case RunFinished(result=r):
                for it in self._iters.values():  # the final text is shown once, below
                    it.box.collapsed = True
                score = (
                    f"score {r.selected_score}" if r.selected_score is not None else "not graded"
                )
                title = f"Final ({r.status}, Iter {r.selected_iteration}, {score})"
                self._add(title, r.final, "final")
            case RunFailed(reason=reason, message=msg):
                self._add("Error", f"{reason}: {msg}", "error")
        self.scroll_end(animate=False)
