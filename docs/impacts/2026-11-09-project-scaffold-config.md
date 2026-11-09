# 2026-11-09 — Project scaffold and configuration

## RU
- **Что изменилось:** создан каркас Python-проекта (uv, ruff, mypy, pytest) и слоистая конфигурация: env `AGORA_*` > YAML (`--config`, `AGORA_CONFIG`, `./config/agora.yaml`) > встроенные дефолты.
- **Зачем:** все параметры reflection-агента (модели, температуры, лимиты) должны настраиваться без правки кода.
- **Влияние:** появился `config/agora.yaml`; ключи API только в `.env` (см. `.env.example`); поле `api_key` в YAML отклоняется с понятной ошибкой. Частичные переопределения модели (например только `temperature`) сохраняют остальные дефолты роли.

## EN
- **What changed:** Python project scaffold (uv, ruff, mypy, pytest) and layered configuration: `AGORA_*` env > YAML (`--config`, `AGORA_CONFIG`, `./config/agora.yaml`) > built-in defaults.
- **Why:** every reflection-agent parameter (models, temperatures, limits) must be configurable without code changes.
- **Impact:** new `config/agora.yaml`; API keys live only in `.env` (see `.env.example`); an `api_key` field in YAML is rejected with a clear error. Partial model overrides (e.g. only `temperature`) keep the role's other defaults.
