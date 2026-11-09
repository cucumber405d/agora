# 2026-11-09 — Reflection service facade

## RU
- **Что изменилось:** `ReflectionService.run(prompt, context, cancel)` отдаёт поток событий прогона и всегда завершается `RunFinished` или `RunFailed`; ошибки провайдера, невалидный ответ критика, пустой промпт и отмена превращаются в события с причиной.
- **Зачем:** UI (сейчас TUI, позже FastAPI) работает только через этот фасад и не знает про LangGraph и Pydantic AI.
- **Влияние:** недоступный Ollama или облачный API больше не роняет приложение: в ленте видно `provider_error` с текстом ошибки. Прогон можно прервать в любой момент.

## EN
- **What changed:** `ReflectionService.run(prompt, context, cancel)` streams run events and always ends with `RunFinished` or `RunFailed`; provider errors, invalid critic output, an empty prompt and cancellation become events with a reason.
- **Why:** the UI (the TUI now, FastAPI later) uses only this facade and knows nothing about LangGraph or Pydantic AI.
- **Impact:** an unreachable Ollama or cloud API no longer crashes the app: the feed shows `provider_error` with the error text. A run can be cancelled at any time.
