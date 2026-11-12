# Agora architecture

Agora is the agentic module of the Appa platform. Cycle 1 (MVP) is a **reflection agent**: a
generator model (high temperature) drafts an answer from a prompt and local files, a critic model
(low temperature) returns a structured verdict, and the loop repeats until the critic approves
with a score at or above the threshold, or the iteration limit is reached. The UI is a Far
Manager / GoldED style console application built with Textual.

Design spec: `docs/superpowers/specs/2026-11-09-agora-mvp-reflection-design.md`.
Change log: `docs/impacts/` (one bilingual RU/EN entry per feature or fix).

## Screen

```
┌ Files: C:\…\Agora ───────────┐┌ Prompt ─────────────────────────────────────────┐
│ [x] Lebenslauf.md            ││ расскажи про меня балладу                       │
│ [ ] notes.txt                │└─────────────────────────────────────────────────┘
└──── Context: 1 files, 3.2k ──┘┌ Run ─ iter 2/3 ─ score 6 → 7 ───────────────────┐
┌ Progress ─ ⠹ 00:47 ──────────┐│ ▸ Iter 1 ─ score 6                              │
│ ████████████░░░░░░░    67%   ││   critique: score 6/10 · feedback · issues      │
│ Gen  ollama/qwen3.5:9b t=0.9 ││ ▾ Iter 2   (streaming draft …)                  │
│ Crit ollama/qwen3:14b t=0.1  │└─────────────────────────────────────────────────┘
│ Loop max 3 iterations, thr 9 │┌ LLM log ────────────────────────────────────────┐
│ 00:00 ✓ It1 Gen 12.7s 37 tk/s││ 00:00 → Gen  qwen3.5:9b 4308 tk  It1: «…»       │
│ 00:12 ✓ It1 Crit 6/10 ✗ 20.4s││ 00:12 ← Gen  512 tk 12.7s stop  Вы — Дмитрий …  │
└──────────────────────────────┘└─────────────────────────────────────────────────┘
 Gen: ollama/qwen3.5:9b t=0.9 │ Critic: ollama/qwen3:14b t=0.1 │ Langfuse ○
 F1 Help F2 Run F3 View F4 Config F5 Copy F6 Save F9 Models F10 Quit  Esc Cancel
```

## Layers

Dependencies point downward only. The core never imports the UI; the UI talks to the core only
through `ReflectionService.run()` and the `RunEvent` stream, so a FastAPI/SSE front end
(cycle 5) can reuse it unchanged.

```
__main__ / tui        entry point, Textual app, panels, dialogs
      │  ReflectionService.run(prompt, context, cancel) -> AsyncIterator[RunEvent]
reflection            LangGraph loop, events, result selection, LLM trace, export
      │
agents   context      Pydantic AI generator/critic, prompts, language | local files -> Context
      │
llm      observability   model factory, health probe | optional Langfuse tracing
      │
config                AppConfig: env > YAML > defaults
```

## Modules

Package root: `src/ibikus/appa/agora/` (`ibikus` and `ibikus.appa` are namespace packages).

### Entry point and infrastructure

| Module | Responsibility |
|---|---|
| `__init__.py` | Version; sets `PYDANTIC_AI_NO_BANNER=1` before Pydantic AI is imported (its banner would corrupt the TUI). |
| `__main__.py` | `agora [--config] [--root] [--version] [doctor [--no-network] | setup | convert FILE]`: loads `.env`, sets up logging, validates configuration and API keys (exit code 2 with a readable message); with no config file anywhere it starts with the Light preset and opens the setup wizard; sets up observability, builds the service factory and the LLM health check, starts the app, flushes traces on exit. |
| `paths.py` | Per-user locations: `~/.agora` (or `AGORA_HOME`) with `config.yaml`, `logs/`, `downloads/`; `is_frozen()` for the PyInstaller build. |
| `logging_setup.py` | File-only logging to `$AGORA_HOME/logs/agora.log` (rotating), level from `AGORA_LOG_LEVEL`; routes Python warnings to the log. Nothing may reach stdout/stderr while the TUI owns the terminal. |

### `config/`

| Module | Responsibility |
|---|---|
| `models.py` | Pydantic models: `ModelConfig` (provider, name, temperature, max_tokens, base_url, timeout_s, max_retries, `think`), `ReflectionConfig` (max_iterations, approve_threshold, `language`, generator, critic, prompts), `ContextConfig`, `ObservabilityConfig`, `AppConfig` (pydantic-settings). Partial overrides keep role defaults only while the provider stays the default one. Unknown fields (e.g. `api_key`) are rejected. |
| `loader.py` | `load_config()`: precedence `AGORA_*` env (`__` for nesting) > YAML (`--config`, `AGORA_CONFIG`, `./config/agora.yaml`, `~/.agora/config.yaml`; `find_config_path()`) > defaults; `ConfigError` lists `field: message` lines. |

### `llm/`

| Module | Responsibility |
|---|---|
| `factory.py` | `build_model()` creates the Pydantic AI model for Ollama (OpenAI-compatible API), Anthropic, OpenAI or OpenRouter; API keys come only from env. `build_settings()` sets temperature, timeout, SDK retries with backoff, `max_tokens`, and for Ollama `think: false` → `reasoning_effort: "none"`. `describe()` gives the status-line label. |
| `health.py` | `check_models()` / `check_config()`: probes each distinct endpoint once (3 s timeout) — Ollama `/api/tags` (server reachable, model pulled), cloud `/models` or `/key` (connection, key accepted). Returns `HealthIssue(roles, problem, hint)`; the TUI shows them in the red error box. |

### `context/`

| Module | Responsibility |
|---|---|
| `models.py` | `Context`, `ContextFile`, `ContextFile.source_format` for converted documents, `SkippedFile` (reason: extension, too_large, not_utf8, over_budget, unreadable, legacy_format, no_text, convert_failed); `estimate_tokens()` ≈ chars / 4 (offline). |
| `documents.py` | `DocumentConverter`: PDF, DOCX, PPTX, XLSX, HTML → Markdown via markitdown, in a worker thread with a timeout, cached by (path, mtime, size). |
| `files.py` | `ContextSource` protocol and `FileContextSource`: reads marked files in order, converts documents, checks extension, size (`max_file_kb` / `max_document_mb`), UTF-8 / binary content and a cumulative token budget; reports conversion progress. Future RAG sources implement the same protocol. |

### `agents/`

| Module | Responsibility |
|---|---|
| `generator.py` | Generator agent (Pydantic AI, free Markdown text, streamed). |
| `critic.py` | Critic agent and the `Critique` verdict: `approved`, `score` 0–10, `feedback` (always), `issues`, `suggestions`. Requested as a JSON-schema constrained response (`NativeOutput`) where supported, else via a tool call; 2 output retries. Validators reject echoed validation messages and inconsistent verdicts (approved with score < 5, rejected without issues). An output validator asks once for Russian when the request is Russian. |
| `prompts.py` | Built-in or custom instruction templates; assembly of the generator input (context, request, previous draft and critique, language) and the critic input (context, request, draft, truncation note, acceptance bar, language). |
| `language.py` | Offline detection of the request language (Russian / German / English) and Cyrillic share for the language check. |
| `templates/*.md` | English instructions: answer-only generator; strict, context-checking critic. |

### `reflection/`

| Module | Responsibility |
|---|---|
| `graph.py` | LangGraph `StateGraph`: `generate → critique → (generate | finalize)`. Emits run events via the custom stream mode, detects truncated drafts (`finish_reason == "length"`), turns a failing critic into `CritiqueFailed`, logs every model exchange. `is_approved()` = critic approval **and** `score >= approve_threshold`; `select_final()` / `to_result()` pick the last draft when approved, otherwise the best-scored one (later wins ties), or the latest ungraded draft on `critic_failed`. |
| `state.py` | `ReflectionState` (prompt, context, iteration, drafts, critiques, truncated flags, critic error). |
| `events.py` | `RunEvent` union: `IterationStarted`, `DraftChunk`, `DraftDone(truncated)`, `CritiqueDone`, `CritiqueFailed`, `LlmExchange`, `RunFinished(RunResult)`, `RunFailed(reason)`. `RunResult` carries status, selected iteration and score, best score and history. |
| `trace.py` | Converts Pydantic AI message history (`capture_run_messages`) into `LlmExchange` entries: requests, responses (tokens, time, finish reason), retries, errors. |
| `service.py` | `ReflectionService` facade: runs the graph in an inner task, streams events through a queue, supports cancellation, maps errors to `RunFailed` (`provider_error`, `generator_failed` with a hint, `invalid_input`, `cancelled`, `internal`). `build_agents()` wires models, settings and instructions. |
| `export.py` | Markdown export of a run (prompt, final answer with selected iteration, every iteration with critique). |

### `observability/`

| Module | Responsibility |
|---|---|
| `langfuse.py` | Optional Langfuse tracing: trace `reflection-run`, spans `iteration-N/generate` and `iteration-N/critique` (score, approved), generations from the Pydantic AI OpenTelemetry instrumentation. `enabled: auto` turns it on when keys are present; any failure degrades to a no-op. |

### `setup/`

No Textual imports: the wizard and `agora doctor` share these modules. Everything external (HTTP, processes, registry, environment) is injected, so tests run without network or Windows.

| Module | Responsibility |
|---|---|
| `runner.py` | `run_command()`: external commands with a timeout; missing binaries and timeouts become result codes, never exceptions. |
| `diagnostics.py` | `collect()` → `SystemReport`: OS, RAM, free disk for Ollama models, GPU (`nvidia-smi`; name only for other GPUs), Ollama installed/running/version/models/`OLLAMA_*` variables. Each check is isolated. Parsers for `nvidia-smi` and `ollama ps`. |
| `presets.py`, `presets.yaml` | Light / Standard / Quality configurations; `recommend()` picks the strongest whose RAM/VRAM requirements are met, `unmet()` explains the others, `disk_shortfall_gb()`. |
| `config_writer.py` | `build_config_data()` applies a preset on top of the existing config; `write_config()` writes atomically and keeps `config.yaml.bak`; `first_run_config()`. |
| `models.py` | `missing_models()`, `pull()` (`/api/pull` NDJSON stream with progress; an error line or a stream without `success` is a `PullError`), `verify()` (1-token request, then `ollama ps`: 100% GPU, context window). |
| `ollama_setup.py`, `winenv.py` | Download (`.part` file, cleaned up on failure or cancel) and launch `OllamaSetup.exe`, wait for the server, recommended `OLLAMA_*` values, restart Ollama; user environment variables in `HKCU\Environment`. |
| `cli.py` | `agora doctor`: report text (✓/⚠/✕ or ASCII), configurations with the recommendation, exit code 0/1/2. |

### `tui/`

| Module | Responsibility |
|---|---|
| `app.py` | `AgoraApp`: layout, F-key bindings (Far order in the footer), run worker, cancellation, F5/F6 actions, F9 model switch, LLM health checks (start-up, after F9, after `provider_error`, before a run when a problem is known), copy to the system clipboard. |
| `files_panel.py` | Far-style file tree: mark with Space/Ins/click on `[ ]`, re-read on reopen and Ctrl+R, parent directory with Backspace/Ctrl+PgUp. |
| `run_feed.py` | Iterations with streamed draft (collapsible), critique (score, feedback, issues, suggestions), truncation and critic-failure warnings, final answer. Model output is rendered as plain text, never as markup. |
| `progress.py` | `RunProgress` (UI-free state model) and `ProgressPanel`: spinner and timer, progress bar, models and loop limits, stage log with durations and tokens/s. |
| `llm_log.py` | `LlmLog`: colour-coded exchange log (requests cyan, responses white, retries yellow, errors red); Enter opens the full text. |
| `status_bar.py` | Active models and Langfuse state. |
| `setup_wizard.py` | `SetupWizard` (F8, first start, `agora setup`): six steps — system, configuration, Ollama, Ollama settings, models, done; downloads run in cancellable workers; `SetupDeps` holds the injected outside world. |
| `dialogs.py` | Help with About (F1), document preview (Enter in the files panel), Markdown viewer (F3), configuration (F4), model switch (F9), LLM error box, LLM log entry viewer. |
| `agora.tcss` | Classic Far palette, high-contrast text dialogs. |

## Run flow

1. F2 → health problems known? re-probe first; empty prompt or a run in progress is rejected.
2. Marked files → `FileContextSource` (documents converted in a thread, progress in the panel) → `Context` (skipped files are reported).
3. `ReflectionService.run()` streams events; the app routes `LlmExchange` to the LLM log and all
   other events to the run feed and the progress panel.
4. `RunFinished` or `RunFailed` ends the run; a `provider_error` triggers the health check and the
   error box.

## Third-party libraries

| Library | Used for |
|---|---|
| Pydantic AI | Agents, provider models, structured output (JSON schema / tool call), retries, message history |
| LangGraph | Reflection loop as a state graph with streaming of custom events |
| Pydantic, pydantic-settings | Data models, validation, layered configuration (env + YAML) |
| Textual, Rich | Console UI, widgets, CSS styling, Pilot-based UI tests |
| httpx | LLM health probes, Ollama API, installer download |
| markitdown | PDF / DOCX / PPTX / XLSX / HTML to Markdown |
| psutil | RAM and disk diagnostics |
| PyInstaller, Inno Setup | Windows build (onedir) and per-user installer |
| Langfuse (OpenTelemetry) | Optional tracing |
| python-dotenv | `.env` loading |
| pyperclip | System clipboard (Git Bash ignores the terminal clipboard sequence) |
| pytest, pytest-asyncio, pytest-textual-snapshot, ruff, mypy | Tests, UI snapshots, lint/format, strict typing |

## Testing

No test touches the network: models are `TestModel`/`FunctionModel`, Ollama responses are
replayed with `httpx.MockTransport` (including SSE streams), the UI is driven with Textual Pilot
and compared with SVG snapshots. `uv run pytest -m integration` runs one smoke test against a real
local Ollama.

## Packaging and release

- `packaging/agora.spec` — PyInstaller onedir build (`dist/agora/agora.exe`) with package data and the metadata of all dependencies.
- `packaging/agora.iss` — Inno Setup, per user (`%LOCALAPPDATA%\Programs\Agora`), Start menu shortcut to `launch.cmd` (Windows Terminal or a sized UTF-8 console), optional PATH entry.
- `scripts/smoke.py` — checks a built exe: `--version`, `doctor --no-network`, document conversion.
- `.github/workflows/release.yml` — on a `v*` tag: tests, build, smoke test, installer, portable zip, GitHub Release with `CHANGELOG.md` from `scripts/changelog.py` (EN parts of `docs/impacts/`).

## Extension points for later cycles

| Cycle | Extension |
|---|---|
| 2 RAG + ChromaDB | another `ContextSource`; optional retrieve node before `generate` |
| 3 Memory (PostgreSQL) | LangGraph checkpointer and session history in `ReflectionState` |
| 4 Tools / MCP | toolsets on the generator agent (Pydantic AI MCP client) |
| 5 FastAPI, multi-agent | HTTP/SSE adapter over `ReflectionService.run`; more graphs and agents |
