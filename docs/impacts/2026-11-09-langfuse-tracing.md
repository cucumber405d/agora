# 2026-11-09 — Optional Langfuse tracing

## RU
- **Что изменилось:** каждый прогон пишется в Langfuse: trace `reflection-run`, span'ы `iteration-N/generate` и `iteration-N/critique` (со score и approved), generations от инструментации Pydantic AI.
- **Зачем:** видеть, как модели и температуры влияют на качество и сколько итераций нужно.
- **Влияние:** режим `observability.langfuse.enabled`: `auto` (по умолчанию — включено, если заданы `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`), `on`, `off`. Недоступный Langfuse не мешает работе: пишется только предупреждение в лог.

## EN
- **What changed:** every run is traced in Langfuse: a `reflection-run` trace, `iteration-N/generate` and `iteration-N/critique` spans (with score and approved), and generations from the Pydantic AI instrumentation.
- **Why:** see how models and temperatures affect quality and how many iterations are needed.
- **Impact:** `observability.langfuse.enabled`: `auto` (default — on when `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` are set), `on`, `off`. An unreachable Langfuse does not affect the app: only a warning is logged.
