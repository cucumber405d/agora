import pytest


@pytest.fixture(autouse=True)
def _posix_title_separator(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """SVG snapshots are recorded on Linux; render the shortened path the same on Windows."""
    if request.node.module.__name__.endswith("test_snapshots"):
        from ibikus.appa.agora.tui import files_panel

        monkeypatch.setattr(files_panel, "PATH_SEP", "/")
