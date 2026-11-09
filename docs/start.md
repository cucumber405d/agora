# Agora - quick start

Build and run commands (reminder).

```bash
uv sync                      # create the virtualenv and install dependencies
cp .env.example .env         # then fill in the API keys you need
uv run agora                 # start the TUI (uses ./config/agora.yaml)
uv run agora --config path/to/agora.yaml

uv run pytest                # unit + TUI tests (no network)
uv run ruff check . && uv run ruff format --check .
uv run mypy src
```
