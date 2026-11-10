from pathlib import Path

from ibikus.appa.agora.context import Context, ContextFile
from ibikus.appa.agora.reflection.events import (
    CritiqueDone,
    CritiqueFailed,
    DraftChunk,
    DraftDone,
    IterationStarted,
    RunFailed,
    RunFinished,
    RunResult,
)
from ibikus.appa.agora.tui.progress import RunProgress

from ..reflection.fakes import c


class Clock:
    def __init__(self) -> None:
        self.t = 100.0

    def __call__(self) -> float:
        return self.t


def _ctx() -> Context:
    return Context(files=[ContextFile(path=Path("a.md"), content="x", tokens=3200)])


def _started(clock: Clock, max_iterations: int = 3) -> RunProgress:
    p = RunProgress(clock=clock)
    p.start(_ctx())
    p.apply(IterationStarted(iteration=1, max_iterations=max_iterations))
    return p


def _result(status: str = "approved", best: int = 9) -> RunResult:
    return RunResult(final="F", status=status, iterations=1, best_score=best, history=[])  # type: ignore[arg-type]


def test_initial_state_idle() -> None:
    p = RunProgress(clock=Clock())
    assert p.state == "idle" and p.lines() == [] and p.percent == 0


def test_context_and_generator_stage() -> None:
    clock = Clock()
    p = _started(clock)
    assert p.state == "running"
    assert p.total_steps == 6 and p.completed_steps == 0
    clock.t += 2
    p.apply(DraftChunk(iteration=1, text="x" * 400))
    lines = p.lines()
    assert lines[0] == "00:00 ✓ Context 1 f 3.2k"
    assert lines[1].startswith("00:00 ") and "It1 Gen ≈100 tk" in lines[1]
    assert p.elapsed() == 2


def test_generator_done_starts_critic() -> None:
    clock = Clock()
    p = _started(clock)
    p.apply(DraftChunk(iteration=1, text="x" * 400))
    clock.t += 4
    p.apply(DraftDone(iteration=1, text="x" * 400))
    lines = p.lines()
    assert lines[1] == "00:00 ✓ It1 Gen 4.0s 25 tk/s"
    assert lines[2].startswith("00:04 ") and lines[2].endswith("It1 Crit")
    assert p.completed_steps == 1


def test_critique_done_shows_score_and_verdict() -> None:
    clock = Clock()
    p = _started(clock)
    p.apply(DraftDone(iteration=1, text="d"))
    clock.t += 3
    p.apply(CritiqueDone(iteration=1, critique=c(6)))
    assert p.lines()[2] == "00:00 ✓ It1 Crit 6/10 ✗ 3.0s"
    assert p.completed_steps == 2
    p.apply(IterationStarted(iteration=2, max_iterations=3))
    p.apply(DraftDone(iteration=2, text="d"))
    p.apply(CritiqueDone(iteration=2, critique=c(9, approved=True)))
    assert "It2 Crit 9/10 ✓" in p.lines()[-1]


def test_early_approval_fills_bar() -> None:
    p = _started(Clock())
    p.apply(DraftDone(iteration=1, text="d"))
    p.apply(CritiqueDone(iteration=1, critique=c(9, approved=True)))
    assert p.percent < 100
    p.apply(RunFinished(result=_result()))
    assert p.state == "done" and p.percent == 100
    assert p.lines()[-1].endswith("✓ Final approved 9")


def test_critique_failed_is_warning() -> None:
    p = _started(Clock())
    p.apply(DraftDone(iteration=1, text="d"))
    p.apply(CritiqueFailed(iteration=1, message="bad"))
    assert "⚠ It1 Crit failed" in p.lines()[-1]
    p.apply(RunFinished(result=_result("critic_failed", 0)))
    assert p.lines()[-1].endswith("⚠ Final critic_failed 0")


def test_cancel_marks_running_stage() -> None:
    p = _started(Clock())
    p.apply(RunFailed(reason="cancelled", message="Run cancelled"))
    assert p.state == "cancelled"
    assert "■ It1 Gen" in p.lines()[1]
    assert p.lines()[-1].endswith("■ cancelled")


def test_provider_error_marks_failed() -> None:
    p = _started(Clock())
    p.apply(RunFailed(reason="provider_error", message="Connection error."))
    assert p.state == "failed"
    assert "✕ It1 Gen" in p.lines()[1]
    assert p.lines()[-1].endswith("✕ provider_error")


def test_title_shows_spinner_then_result() -> None:
    clock = Clock()
    p = _started(clock)
    clock.t += 23
    assert p.title().endswith(" 00:23") and p.title()[0] in RunProgress.SPINNER
    p.apply(RunFinished(result=_result()))
    clock.t += 100  # the timer stops when the run ends
    assert p.title() == "✓ 00:23"


def test_restart_clears_previous_run() -> None:
    p = _started(Clock())
    p.apply(RunFinished(result=_result()))
    p.start(Context.empty())
    assert p.state == "running" and p.lines() == ["00:00 ✓ Context 0 f 0.0k"]


def test_generator_waiting_for_first_token() -> None:
    p = _started(Clock())
    assert p.lines()[1].endswith("It1 Gen waiting…")
    p.apply(DraftChunk(iteration=1, text="x" * 8))
    assert p.lines()[1].endswith("It1 Gen ≈2 tk")


def test_truncated_generation_is_warning() -> None:
    clock = Clock()
    p = _started(clock)
    clock.t += 2
    p.apply(DraftDone(iteration=1, text="x" * 40, truncated=True))
    assert "⚠ It1 Gen" in p.lines()[1] and p.lines()[1].endswith("truncated")
