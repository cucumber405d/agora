"""Real-model smoke test. Run with: uv run pytest -m integration"""

import os
import urllib.request

import pytest

from ibikus.appa.agora.config import AppConfig
from ibikus.appa.agora.context import Context
from ibikus.appa.agora.reflection.events import RunFailed, RunFinished
from ibikus.appa.agora.reflection.service import ReflectionService

OLLAMA = os.environ.get("AGORA_TEST_OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("AGORA_TEST_OLLAMA_MODEL", "qwen2.5:7b")


def _ollama_up() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=2):
            return True
    except OSError:
        return False


@pytest.mark.integration
async def test_reflection_run_with_ollama() -> None:
    if not _ollama_up():
        pytest.skip(f"Ollama not reachable at {OLLAMA}")
    role = {"provider": "ollama", "name": MODEL, "base_url": f"{OLLAMA}/v1"}
    cfg = AppConfig.model_validate(
        {
            "reflection": {
                "max_iterations": 2,
                "generator": {**role, "temperature": 0.9},
                "critic": {**role, "temperature": 0.1},
            }
        }
    )
    events = [e async for e in ReflectionService(cfg).run("What is 2 + 2?", Context.empty())]
    last = events[-1]
    assert not isinstance(last, RunFailed), last
    assert isinstance(last, RunFinished)
    assert last.result.final.strip()
