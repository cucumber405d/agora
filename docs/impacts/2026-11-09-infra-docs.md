# 2026-11-09 — Langfuse self-hosting, CI and documentation

## RU
- **Что изменилось:** добавлены `docker/langfuse/compose.yaml` (официальный self-hosting Langfuse, образы закреплены на мажорной версии 4) с инструкцией, CI на GitHub Actions (ruff, mypy, pytest), документация `docs/architecture.md`, `docs/configuration.md`, `docs/troubleshooting.md`, обновлён `docs/start.md`, интеграционный тест с реальным Ollama (`uv run pytest -m integration`).
- **Зачем:** локальный трейсинг без внешних сервисов, автоматическая проверка каждого push и документация как код.
- **Влияние:** интеграционный тест пропускается, если Ollama недоступен; модель и адрес задаются через `AGORA_TEST_OLLAMA_MODEL` / `AGORA_TEST_OLLAMA_URL`.

## EN
- **What changed:** added `docker/langfuse/compose.yaml` (official Langfuse self-hosting, images pinned to major version 4) with instructions, GitHub Actions CI (ruff, mypy, pytest), docs `docs/architecture.md`, `docs/configuration.md`, `docs/troubleshooting.md`, updated `docs/start.md`, and an integration test against a real Ollama (`uv run pytest -m integration`).
- **Why:** local tracing without external services, automatic checks on every push, and documentation as code.
- **Impact:** the integration test is skipped when Ollama is unreachable; model and URL are set via `AGORA_TEST_OLLAMA_MODEL` / `AGORA_TEST_OLLAMA_URL`.
