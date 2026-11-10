"""Shared helpers for TUI tests."""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from textual.pilot import Pilot

from ibikus.appa.agora.agents.critic import Critique
from ibikus.appa.agora.config import AppConfig
from ibikus.appa.agora.reflection.service import ReflectionService
from ibikus.appa.agora.tui.app import AgoraApp
from ibikus.appa.agora.tui.files_panel import FilesPanel

from ..reflection.fakes import c, make_agents


def make_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "a.md").write_text("hello", encoding="utf-8")
    (root / "b.txt").write_text("world", encoding="utf-8")
    return root


def factory(
    drafts: Sequence[str | Exception] = ("Answer",),
    critiques: Sequence[Critique | Exception] | None = None,
    *,
    chunk_delay: float = 0.0,
    calls: list[AppConfig] | None = None,
) -> Callable[[AppConfig], ReflectionService]:
    crits = list(critiques) if critiques is not None else [c(9, approved=True)]

    def build(cfg: AppConfig) -> ReflectionService:
        if calls is not None:
            calls.append(cfg)
        return ReflectionService(
            cfg, agents=make_agents(list(drafts), crits, chunk_delay=chunk_delay)
        )

    return build


def make_app(root: Path, **kw: Any) -> AgoraApp:
    return AgoraApp(AppConfig(), root=root, service_factory=factory(**kw))


class NotifyRecorder:
    def __init__(self, app: AgoraApp) -> None:
        self.messages: list[str] = []
        original = app.notify

        def record(message: str, *args: Any, **kwargs: Any) -> None:
            self.messages.append(message)
            original(message, *args, **kwargs)

        app.notify = record  # type: ignore[method-assign]


async def wait_tree(pilot: Pilot[Any]) -> FilesPanel:
    panel = pilot.app.query_one(FilesPanel)
    for _ in range(50):
        await pilot.pause(0.02)
        if any(n.data and n.data.path.name == "a.md" for n in _nodes(panel)):
            return panel
    raise AssertionError("directory tree did not load")


def _nodes(panel: FilesPanel) -> list[Any]:
    out, stack = [], [panel.root]
    while stack:
        node = stack.pop()
        out.append(node)
        stack.extend(node.children)
    return out


async def mark(pilot: Pilot[Any], name: str) -> None:
    panel = await wait_tree(pilot)
    node = next(n for n in _nodes(panel) if n.data and n.data.path.name == name)
    panel.focus()
    panel.move_cursor(node)
    await pilot.press("space")
    await pilot.pause()


async def wait_run(app: Any) -> None:
    """Wait for the reflection worker only (DirectoryTree keeps its own loader running)."""
    await wait_group(app, "run")


async def wait_group(app: Any, group: str) -> None:
    """Wait for all workers of one group to finish."""
    import asyncio

    from textual.worker import WorkerCancelled

    for w in [w for w in app.workers if w.group == group]:
        with contextlib.suppress(WorkerCancelled):
            await asyncio.wait_for(w.wait(), 10)


async def run_prompt(pilot: Pilot[Any], text: str) -> None:
    await wait_tree(pilot)
    prompt = pilot.app.query_one("#prompt")
    prompt.focus()
    prompt.insert(text)  # type: ignore[attr-defined]
    await pilot.press("f2")
    await pilot.pause()
    await wait_run(pilot.app)
    await pilot.pause()
