# Agora architecture (MVP)

Agora is the agentic module of the Appa platform. The MVP is a **reflection agent**: a generator
model (high temperature) drafts an answer, a critic model (low temperature) reviews it, and the
loop repeats until the critic approves or the iteration limit is reached. The UI is a Far-style
Textual TUI.

Design spec: `docs/superpowers/specs/2026-11-09-agora-mvp-reflection-design.md`.

## Layers

Dependencies point downward only; the core never imports the UI.

```
tui/            Textual app: FilesPanel, prompt TextArea, RunFeed, StatusBar, dialogs
  │ uses only ReflectionService.run() and RunEvent
reflection/     service.py (facade), graph.py (LangGraph), events.py, state.py, export.py
  │
agents/         generator / critic (Pydantic AI), prompt assembly, built-in templates
llm/            ModelConfig -> pydantic_ai Model (ollama / anthropic / openai / openrouter)
context/        FileContextSource: extension, size, UTF-8, cumulative token budget
observability/  optional Langfuse tracing (no-op when not configured)
config/         AppConfig (pydantic-settings): env > YAML > defaults
```

## Reflection graph

```
START -> generate -> critique --approved or score >= threshold--> finalize -> END
            ^            |
            +-- not approved and iteration < max_iterations
                         +-- iteration >= max_iterations -------> finalize
```

- `generate` streams tokens (`DraftChunk`) via LangGraph's custom stream mode
  (`get_stream_writer`). From iteration 2 it receives the previous draft and critique.
- `critique` returns a typed `Critique` (`approved`, `score` 0-10, `issues`, `suggestions`),
  with 2 output retries; failure becomes `CriticInvalidError`.
- The final answer is the last draft when approved, otherwise the highest-scored draft
  (later wins ties).

## Run events

`ReflectionService.run(prompt, context, cancel)` yields:
`IterationStarted`, `DraftChunk`, `DraftDone`, `CritiqueDone`, and ends with exactly one of
`RunFinished(result)` or `RunFailed(reason, message)`, where reason is one of
`cancelled`, `provider_error`, `critic_invalid`, `invalid_input`, `internal`.

The graph runs in an inner task that feeds a queue; cancellation (`asyncio.Event`) cancels the
task and yields `RunFailed("cancelled")`.

## Observability

With Langfuse enabled, each run is a `reflection-run` trace (type agent) with
`iteration-N/generate` and `iteration-N/critique` spans; model calls are recorded as generations
by the Pydantic AI OpenTelemetry instrumentation (`Agent.instrument_all()`).

## Extension points for later cycles

| Cycle | Extension |
|---|---|
| 2 RAG + ChromaDB | another `ContextSource` implementation; optional retrieve node before `generate` |
| 3 Memory (PostgreSQL) | LangGraph checkpointer + session history in `ReflectionState` |
| 4 Tools / MCP | toolsets on the generator agent (Pydantic AI MCP client) |
| 5 FastAPI, multi-agent | HTTP/SSE adapter over `ReflectionService.run`; more graphs/agents |
