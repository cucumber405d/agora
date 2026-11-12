"""Run progress: a UI-free state model (RunProgress) and the panel that renders it.

The panel lives under the file panel, like Far's info panel (Ctrl+L toggles it). It shows a
spinner with elapsed time, a progress bar (generator + critic steps per iteration) and a log of
stages. Everything is derived from the same RunEvents the run feed consumes.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import ProgressBar, Static

from ibikus.appa.agora.context import Context, estimate_tokens
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

ProgressState = Literal["idle", "running", "done", "failed", "cancelled"]
StageState = Literal["running", "done", "warn", "failed", "cancelled"]

_ICONS: dict[StageState, str] = {"done": "✓", "warn": "⚠", "failed": "✕", "cancelled": "■"}


@dataclass
class _Stage:
    started: float
    label: str
    state: StageState = "running"
    detail: str = ""
    chars: int = 0


def _mmss(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60:02d}:{s % 60:02d}"


class RunProgress:
    SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.state: ProgressState = "idle"
        self.total_steps = 0
        self.completed_steps = 0
        self._stages: list[_Stage] = []
        self._t0 = 0.0
        self._t_end: float | None = None
        self._header: list[str] = []

    # -- input ----------------------------------------------------------------------------------

    def start(
        self,
        context: Context,
        generator: str | None = None,
        critic: str | None = None,
        limits: str | None = None,
    ) -> None:
        self._header = [
            line
            for line in (
                f"Gen  {generator}" if generator else None,
                f"Crit {critic}" if critic else None,
                f"Loop {limits}" if limits else None,
            )
            if line
        ]
        self.state = "running"
        self.total_steps = self.completed_steps = 0
        self._t0 = self.clock()
        self._t_end = None
        self._stages = [
            _Stage(
                self._t0,
                f"Context {len(context.files)} f {context.total_tokens / 1000:.1f}k",
                "done",
            )
        ]

    def _current(self) -> _Stage | None:
        return self._stages[-1] if self._stages and self._stages[-1].state == "running" else None

    def _finish_current(self, state: StageState, detail: str) -> None:
        stage = self._current()
        if stage is not None:
            stage.state, stage.detail = state, detail

    def apply(self, event: RunEvent) -> None:
        now = self.clock()
        match event:
            case IterationStarted(iteration=n, max_iterations=m):
                self.total_steps = 2 * m
                self._stages.append(_Stage(now, f"It{n} Gen", detail="waiting…"))
            case DraftChunk(text=t):
                stage = self._current()
                if stage is not None:
                    stage.chars += len(t)
                    stage.detail = f"≈{estimate_tokens('x' * stage.chars)} tk"
            case DraftDone(iteration=n, text=t, truncated=cut):
                stage = self._current()
                took = now - stage.started if stage else 0.0
                tokens = estimate_tokens(t)
                rate = f" {tokens / took:.0f} tk/s" if took > 0 else ""
                if cut:
                    self._finish_current("warn", f"{took:.1f}s{rate} truncated")
                else:
                    self._finish_current("done", f"{took:.1f}s{rate}")
                self.completed_steps += 1
                self._stages.append(_Stage(now, f"It{n} Crit"))
            case CritiqueDone(critique=c):
                stage = self._current()
                took = now - stage.started if stage else 0.0
                verdict = "✓" if c.approved else "✗"
                self._finish_current("done", f"{c.score}/10 {verdict} {took:.1f}s")
                self.completed_steps += 1
            case CritiqueFailed():
                self._finish_current("warn", "failed")
                self.completed_steps += 1
            case RunFinished(result=r):
                self.completed_steps = self.total_steps
                icon_state: StageState = "done" if r.status == "approved" else "warn"
                score = f"{r.selected_score}/10" if r.selected_score is not None else "not graded"
                label = f"Final It{r.selected_iteration} {score} {r.status}"
                self._stages.append(_Stage(now, label, icon_state))
                self._end("done", now)
            case RunFailed(reason=reason):
                state: StageState = "cancelled" if reason == "cancelled" else "failed"
                current = self._current()
                self._finish_current(state, current.detail if current is not None else "")
                self._stages.append(_Stage(now, reason, state))
                self._end("cancelled" if reason == "cancelled" else "failed", now)

    def _end(self, state: ProgressState, now: float) -> None:
        self.state = state
        self._t_end = now

    # -- output ---------------------------------------------------------------------------------

    def elapsed(self) -> float:
        if self.state == "idle":
            return 0.0
        return (self._t_end if self._t_end is not None else self.clock()) - self._t0

    @property
    def percent(self) -> int:
        return 100 * self.completed_steps // self.total_steps if self.total_steps else 0

    def _spinner(self) -> str:
        return self.SPINNER[int(self.elapsed() * 10) % len(self.SPINNER)]

    def lines(self) -> list[str]:
        out = list(self._header)
        for st in self._stages:
            icon = self._spinner() if st.state == "running" else _ICONS[st.state]
            tail = f" {st.detail}" if st.detail else ""
            out.append(f"{_mmss(st.started - self._t0)} {icon} {st.label}{tail}")
        return out

    def title(self) -> str:
        if self.state == "idle":
            return ""
        icon = {"running": self._spinner(), "done": "✓", "failed": "✕", "cancelled": "■"}
        return f"{icon[self.state]} {_mmss(self.elapsed())}"


class ProgressPanel(Vertical):
    """Renders RunProgress; ticks 10x per second while a run is in progress."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.progress = RunProgress()
        self.history: list[str] = []  # context-stage lines shown in this session

    def context_progress(self, done: int, total: int) -> None:
        """Show document conversion progress before the run's own stages start."""
        line = f"Context: converting {done}/{total}"
        self.history.append(line)
        self.border_title = "Progress ─ context"
        self.query_one(ProgressBar).update(progress=100 * done // max(total, 1))
        self.query_one("#progress-log", Static).update(Text(line))

    def compose(self) -> ComposeResult:
        yield ProgressBar(total=100, show_eta=False, id="progress-bar")
        with VerticalScroll(id="progress-scroll"):
            yield Static("", id="progress-log")

    def on_mount(self) -> None:
        self.border_title = "Progress"
        self.set_interval(0.1, self._tick)

    def start(
        self,
        context: Context,
        generator: str | None = None,
        critic: str | None = None,
        limits: str | None = None,
    ) -> None:
        self.progress.start(context, generator, critic, limits)
        self._redraw()

    def apply(self, event: RunEvent) -> None:
        self.progress.apply(event)
        self._redraw()

    def _tick(self) -> None:
        if self.progress.state == "running":
            self._redraw()

    def _redraw(self) -> None:
        title = self.progress.title()
        self.border_title = f"Progress ─ {title}" if title else "Progress"
        self.query_one(ProgressBar).update(progress=self.progress.percent)
        self.query_one("#progress-log", Static).update(Text("\n".join(self.progress.lines())))
        self.query_one("#progress-scroll", VerticalScroll).scroll_end(animate=False)
