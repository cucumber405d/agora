# Agora - quick start

Build and run commands (reminder).

```bash
uv sync                      # create the virtualenv and install dependencies
cp .env.example .env         # then fill in the API keys you need
uv run agora                 # start the TUI (uses ./config/agora.yaml)
uv run agora --config path/to/agora.yaml --root path/to/files

uv run pytest                # unit + TUI tests (no network)
uv run pytest -m integration # real Ollama smoke test (skipped if Ollama is down)
uv run pytest tests/tui --snapshot-update   # regenerate TUI snapshots after UI changes
uv run ruff check . && uv run ruff format --check .
uv run mypy src

# optional: Langfuse tracing
docker compose -f docker/langfuse/compose.yaml up -d   # UI: http://localhost:3000
```

Keys in the TUI: F1 help, F2 run, F3 view, F4 config, F5 copy, F6 save, F9 models, F10 quit,
Esc cancel, Space/Ins or click on [ ] mark a file, Ctrl+R re-read the file panel,
Backspace/Ctrl+PgUp parent directory, Ctrl+L show/hide the progress panel.

More: `docs/architecture.md`, `docs/configuration.md`, `docs/troubleshooting.md`.
