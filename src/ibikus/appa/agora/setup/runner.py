"""Injectable external-command runner (tests replace it with fakes)."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[Sequence[str], float], CommandResult]

NOT_FOUND = 127
TIMED_OUT = 124


def run_command(args: Sequence[str], timeout_s: float = 10) -> CommandResult:
    """Run a command and capture its output; never raises for missing binaries or timeouts."""
    try:
        done = subprocess.run(  # fixed argument lists, no shell
            list(args),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError:
        return CommandResult(NOT_FOUND, "", f"{args[0]}: not found")
    except subprocess.TimeoutExpired:
        return CommandResult(TIMED_OUT, "", f"{args[0]}: timed out after {timeout_s:g}s")
    except OSError as e:
        return CommandResult(NOT_FOUND, "", f"{args[0]}: {e}")
    return CommandResult(done.returncode, done.stdout, done.stderr)
