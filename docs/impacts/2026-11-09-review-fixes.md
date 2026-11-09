# 2026-11-09 — Fixes from the final code review

## RU
- **Что изменилось:**
  - При смене провайдера роли (в YAML, через env или по `F9`) больше не наследуются имя модели и Ollama-`base_url` от значений по умолчанию; без `name` для нового провайдера — понятная ошибка конфигурации.
  - Новый прогон сбрасывает прошлый результат, поэтому `F3`/`F5`/`F6` после отменённого или неудачного прогона не выдают старый ответ под новым промптом.
  - Ошибка записи в `F6` показывается сообщением, а не роняет TUI.
  - Отсутствующий или нечитаемый файл промпта (`reflection.prompts.*`) — ошибка конфигурации с кодом выхода 2 вместо traceback.
- **Зачем:** запросы OpenAI уходили бы на локальный Ollama; сохранённый файл прогона мог содержать чужой ответ; два сценария приводили к падению.
- **Влияние:** при смене провайдера в YAML нужно явно указывать `name`.

## EN
- **What changed:**
  - Switching a role's provider (in YAML, via env or with `F9`) no longer inherits the default model name or the Ollama `base_url`; a missing `name` for the new provider is a clear configuration error.
  - A new run clears the previous result, so `F3`/`F5`/`F6` after a cancelled or failed run no longer return an old answer under the new prompt.
  - A write error in `F6` is shown as a message instead of crashing the TUI.
  - A missing or unreadable prompt file (`reflection.prompts.*`) is a configuration error with exit code 2 instead of a traceback.
- **Why:** OpenAI requests would have gone to the local Ollama; a saved run file could contain another run's answer; two scenarios crashed the app.
- **Impact:** when switching provider in YAML, `name` must be given explicitly.
