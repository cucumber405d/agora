# Agora MVP — Reflection Agent with Far-style TUI

- **Date:** 2026-11-09
- **Status:** Draft, awaiting review
- **Cycle:** 1 of 5 (MVP)
- **Package:** `ibikus.appa.agora`

## 1. Goal

Agora is the agentic / multi-agent module of the Appa platform. This first cycle covers only the
core: a **reflection agent** that answers a user prompt using attached context. A *generator*
model with a high temperature writes a draft, and a *critic* model with a low temperature
(the same model or another one) reviews it. The loop runs until the critic approves the draft
or the iteration limit is reached. Everything is configurable.

The app runs as a **text console application in Far Manager / GoldED style** (Textual TUI).

It is also a portfolio piece, so clean layering, tests, CI and docs-as-code are part of the scope.

### Roadmap (out of scope here; each cycle gets its own spec)

1. **MVP** (this spec): reflection loop, config, TUI, Langfuse tracing, tests
2. RAG + ChromaDB as a context source
3. Memory layer (PostgreSQL), session history
4. Tool calling / MCP
5. FastAPI layer, Docker/K8s, multi-agent scenarios

## 2. Decisions

| Topic | Decision |
|---|---|
| UI | Textual TUI, Far/GoldED look (blue theme, panels, F-key bar) |
| UI and code-comment language | English |
| LLM providers | Configurable per role: Ollama (local), Anthropic, OpenAI, OpenRouter |
| Stop criterion | Structured `Critique` verdict: `approved` or `score >= threshold`, capped by `max_iterations` |
| Context | Prompt + local files picked in a Far-like file panel |
| Observability | Langfuse, self-hosted via `docker compose`; optional (no keys → no-op) |
| Orchestration | LangGraph `StateGraph`; each node wraps a Pydantic AI agent |

## 3. Architecture

Dependencies only point downward. The core does not know about the UI.

```
src/ibikus/appa/agora/
├── config/        # pydantic-settings: AppConfig, ModelConfig, ReflectionConfig; YAML + .env loading
├── llm/           # model factory: ModelConfig -> pydantic_ai Model (ollama/anthropic/openai/openrouter)
├── agents/        # generator.py, critic.py (Pydantic AI agents); prompt templates
├── reflection/    # state.py (ReflectionState), graph.py (StateGraph), events.py (RunEvent), service.py
├── context/       # ContextSource protocol; FileContextSource (size/token limits, extensions)
├── observability/ # Langfuse init; no-op when not configured
├── tui/           # Textual app: screens, panels, keybindings, .tcss
└── __main__.py    # `agora [--config PATH]`
tests/  docs/  config/agora.yaml  prompts/  docker/langfuse/compose.yaml  pyproject.toml
```

### 3.1 Data model

- `ModelConfig`: `provider`, `name`, `temperature`, `max_tokens`, `base_url?`. API keys come only from env.
- `ReflectionConfig`: `generator: ModelConfig`, `critic: ModelConfig`, `max_iterations`, `approve_threshold`, prompt paths.
- `Critique` (critic output type): `approved: bool`, `score: int (0..10)`, `issues: list[str]`, `suggestions: list[str]`.
- `ReflectionState`: `prompt`, `context`, `iteration`, `drafts[]`, `critiques[]`, `final`, `status`.
- `RunEvent` (discriminated union): `IterationStarted`, `DraftChunk`, `DraftDone`, `CritiqueDone`, `RunFinished`, `RunFailed`.

### 3.2 Service facade

`ReflectionService.run(prompt: str, context: Context) -> AsyncIterator[RunEvent]` is the only
entry point to the core. The TUI uses it now; FastAPI will use it in cycle 5.

### 3.3 Tooling

Python 3.12, `uv`, `ruff` (lint + format), `pytest` + `pytest-asyncio`, `mypy --strict` for the
core packages, GitHub Actions CI.

## 4. Reflection graph

```
generate --> critique --> route
   ^                        |
   |-- not approved, iter < max
                            |-- approved or score >= threshold --> finalize (status=approved)
                            |-- iter >= max_iterations          --> finalize (status=max_iterations)
```

- **generate.** On iteration 1 the input is the system prompt, then the context (each file under
  a `### file: <path>` header), then the user request. From iteration 2 on, the previous draft
  and its critique are added, with an instruction to revise the draft against the critique.
  Tokens are streamed as `DraftChunk` events.
- **critique.** The critic sees the request, the context and the draft, and must return a
  `Critique`. Pydantic AI output retries: 2.
- **finalize.** With `approved`, the result is the last draft. With `max_iterations`, it is the
  draft with the **highest score** (on a tie, the latest one).
- **Events.** Nodes emit `RunEvent`s through the LangGraph custom stream mode. The service
  re-exposes them as an async iterator.
- **Cancellation.** Esc cancels the asyncio task; the service emits `RunFailed(reason="cancelled")`.
- **Langfuse.** One trace per run, one span per iteration, one generation per model call.
  Metadata: model, temperature, score.

## 5. TUI (Textual)

```
┌ Files ─────────────────┐┌ Prompt ────────────────────────────────────────┐
│ ..                     ││ Explain the difference between ...             │
│ [x] docs/notes.md      ││                                                │
│ [ ] src/main.py        │├ Run ─ iter 2/3 ─ score 6 → 8 ─────────────────┤
│ [x] spec.txt           ││ ▸ Iter 1  draft  ▸ critique (score 6)          │
│                        ││ ▾ Iter 2  draft (streaming...)                 │
│ Context: 2 files, 3.1k ││   ... █                                        │
└────────────────────────┘└────────────────────────────────────────────────┘
 Gen: ollama/qwen2.5 t=0.9 │ Critic: anthropic/claude-haiku t=0.1 │ Langfuse ●
 F1 Help F2 Run F3 View F4 Config F5 Copy F6 Save F9 Models F10 Quit  Esc Cancel
```

- **Files panel:** browser rooted at the working directory. `Space`/`Ins` marks a file. The footer
  shows the file count and the estimated context tokens.
- **Prompt editor:** multi-line. `Ctrl+Enter` or `F2` starts a run.
- **Run feed:** one collapsible block per iteration, with the streaming draft and the critique
  (score, issues). The final answer is highlighted.
- **Status line:** the active models, their temperatures, and the Langfuse state.
- **Keys:** `F1` help · `F2` run · `F3` full-screen Markdown viewer for the final answer ·
  `F4` read-only config view · `F5` copy the final answer · `F6` save the final answer plus the
  iteration history as Markdown · `F9` model/temperature dialog (session only, YAML is never
  rewritten) · `F10` quit · `Esc` cancel the run.
- Classic Far blue theme in `.tcss`. Works in Windows Terminal and WSL2. Mouse is supported, but
  every action is reachable from the keyboard.

## 6. Configuration

Precedence (highest first): env `AGORA_*` (nested fields use `__`) > file from `--config` >
`AGORA_CONFIG` > `./config/agora.yaml` > built-in defaults.
Secrets (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `LANGFUSE_*`) are read only
from env or `.env` and never from YAML.

```yaml
reflection:
  max_iterations: 3
  approve_threshold: 8
  generator: { provider: ollama, name: qwen2.5:7b, temperature: 0.9, base_url: http://localhost:11434/v1 }
  critic:    { provider: anthropic, name: claude-haiku-4-5, temperature: 0.1 }
  prompts:   { generator: prompts/generator.md, critic: prompts/critic.md }
context: { max_file_kb: 256, max_total_tokens: 32000, allowed_ext: [.md, .txt, .py, .java, .yaml, .json] }
observability: { langfuse: { enabled: auto } }   # auto = on when keys are present
```

## 7. Error handling

| Situation | Behaviour |
|---|---|
| Invalid config | Readable pydantic error that names the field; printed before the TUI starts; exit code 2 |
| Provider down / timeout / 429 | 3 retries with backoff, then `RunFailed`, shown in the run feed; the app keeps running |
| Critic output invalid | Output retries, then `RunFailed(reason="critic_invalid")` |
| Context over limit | Warning in the files panel; files over the limit are not sent |
| Langfuse unreachable | Warning in the log only; no functional impact |
| Logging | `~/.agora/logs/agora.log` (never stdout, so the TUI is not corrupted) |

## 8. Testing (TDD)

- **Unit:** config loading, env override, validation; model factory; prompt assembly;
  `FileContextSource` limits and extensions; graph routing.
- **Graph:** run with `pydantic_ai.models.test.TestModel` / `FunctionModel`, no network.
  Scenarios: approved on iteration 1; improves until it reaches the threshold; hits the limit and
  picks the best draft; critic output invalid; cancellation.
- **TUI:** Textual `App.run_test()` + `Pilot` (mark a file, type a prompt, press F2, assert the
  events in the feed); snapshot tests with `pytest-textual-snapshot`.
- **Integration:** real Ollama tests marked `@pytest.mark.integration`, skipped by default.
- **CI:** `ruff check`, `ruff format --check`, `mypy`, `pytest` on GitHub Actions.

## 9. Project conventions

- The UI text and all source-code comments are in **English**.
- **Docs as code:** `docs/start.md` (build/run commands), `docs/architecture.md`,
  `docs/configuration.md`, `docs/troubleshooting.md`.
- **Impacts:** every feature, fix or bug gets an entry in `docs/impacts/`, in **Russian and
  English**. One file per change: `docs/impacts/YYYY-MM-DD-<slug>.md`, with sections
  `## RU` and `## EN`, each covering *what changed*, *why*, and *impact* (user-visible effects,
  config changes, migration notes).

## 10. Out of scope (YAGNI)

RAG, cross-session memory, tools/MCP, FastAPI, K8s, persisting sessions to a DB, editing the YAML
from the TUI.
