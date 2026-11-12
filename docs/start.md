# Agora - quick start

Commands to build and run Agora with local models (Windows: Git Bash; Linux/macOS: any shell).

## 1. Prerequisites

- [uv](https://docs.astral.sh/uv/) — installs Python 3.12 and all dependencies.
- [Ollama](https://ollama.com/download) for local models (Windows: `OllamaSetup.exe` or
  `winget install Ollama.Ollama`). It runs in the tray and serves `http://localhost:11434`.
- A GPU helps a lot: with 12 GB VRAM a 14B model plus an 8k context fits entirely on the GPU.

## 2. Ollama setup (once)

```bash
ollama --version                 # in a NEW terminal after installing
ollama pull qwen3.5:9b           # generator (~5.7 GB)
ollama pull qwen3:14b            # critic (~9 GB)
ollama list
```

Context window — Ollama defaults to 4096 tokens, too small for prompts with files:

- Ollama app → Settings → **Context length: 8k** (or 16k if VRAM allows), or the user
  environment variable `OLLAMA_CONTEXT_LENGTH=8192`. Use one of the two, not both.
- Smaller KV cache, same quality — user environment variables (not available in the app UI):
  `OLLAMA_FLASH_ATTENTION=1` and `OLLAMA_KV_CACHE_TYPE=q8_0`.
- After changing variables: tray → Quit, start Ollama again, open a new terminal.

Check right after a model has answered:

```bash
ollama run qwen3:14b "hi"
ollama ps                        # want: CONTEXT 8192 and PROCESSOR 100% GPU
```

## 3. Agora setup

```bash
uv sync                          # create the virtualenv and install dependencies
cp .env.example .env             # only needed for cloud models or Langfuse
```

`config/agora.yaml` for the local pair above (context budget = Ollama window minus ~3.5k):

```yaml
reflection:
  max_iterations: 3
  approve_threshold: 9             # accept only if the critic approves AND score >= 9
  language: auto                   # answer/critique in the prompt language
  generator: {provider: ollama, name: qwen3.5:9b, temperature: 0.9,
              base_url: http://localhost:11434/v1, think: false}
  critic:    {provider: ollama, name: qwen3:14b, temperature: 0.1,
              base_url: http://localhost:11434/v1, think: false}
context:
  max_file_kb: 256
  max_total_tokens: 4500           # 8k window; use 12000 for a 16k window
  allowed_ext: [.md, .txt, .py, .java, .yaml, .json]
observability:
  langfuse: {enabled: auto}
```

`think: false` switches off the hidden reasoning phase of qwen3 / qwen3.5 models (faster, and the
context is not used up by reasoning). Without a GPU, use a smaller pair such as `qwen2.5:7b`.

## 4. Run

```bash
uv run agora                     # uses ./config/agora.yaml
uv run agora --config path/to/agora.yaml --root path/to/files
```

At start-up Agora probes the models; if Ollama is not running or a model is missing, a red
"LLM not available" box says what to do (Retry / Models (F9) / Close).

Keys: F1 help, F2 run (Ctrl+Enter), F3 view answer, F4 config, F5 copy answer, F6 save run
(`./agora-runs/`), F9 models, F10 quit, Esc cancel / close. File panel: Space/Ins or click on
`[ ]` marks a file, Ctrl+R re-reads; parent directory: `..` (Enter/click), Ctrl+PgUp from
anywhere, or Backspace in the file panel.
Ctrl+L shows/hides the progress panel. LLM log: Enter opens the full request/response.
In text windows: F7 selects all, Ctrl+C copies. Logs: `~/.agora/logs/agora.log`.

## 5. Develop

```bash
uv run pytest                    # unit + UI tests (no network)
uv run pytest -m integration     # real Ollama smoke test (skipped if Ollama is down)
uv run pytest tests/tui --snapshot-update   # regenerate UI snapshots after UI changes
uv run ruff check . && uv run ruff format --check .
uv run mypy src
```

## 6. Optional: cloud models and Langfuse

- Cloud critic: put `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`, `OPENROUTER_API_KEY`) into `.env`
  and set e.g. `critic: {provider: anthropic, name: claude-haiku-4-5, temperature: 0.1}`.
- Tracing: `docker compose -f docker/langfuse/compose.yaml up -d` (UI http://localhost:3000),
  then put the Langfuse keys into `.env` (see `docker/langfuse/README.md`).

More: `docs/architecture.md`, `docs/configuration.md`, `docs/troubleshooting.md`.

## Setup wizard and diagnostics

- On the first start without any config file Agora opens the setup wizard; later open it with `F8` or `agora setup`.
- `agora doctor` prints system and Ollama diagnostics in the console (see [troubleshooting](troubleshooting.md)).

## Building the Windows installer locally

```bash
uv sync
uv run pyinstaller packaging/agora.spec --noconfirm      # -> dist/agora/agora.exe
uv run python scripts/smoke.py dist/agora/agora.exe 0.2.0
iscc /DAppVersion=0.2.0 packaging/agora.iss              # -> dist/Agora-Setup-0.2.0.exe (Inno Setup 6)
```

Releases are built by GitHub Actions on a `v*` tag (see `.github/workflows/release.yml`).
