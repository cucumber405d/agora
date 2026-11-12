import os

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_agora_home(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Never read or write the developer's real ~/.agora from tests."""
    from ibikus.appa.agora import paths

    home = tmp_path_factory.mktemp("agora-home")
    monkeypatch.setattr(paths, "_default_home", lambda: home)
    return home
