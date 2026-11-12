# 2026-11-12 — Config writer

## RU
- **Что изменилось:** `setup/config_writer.py` строит конфиг из выбранной конфигурации (модели Ollama с `think: false`, язык `auto`, бюджет контекста) поверх существующего файла и записывает его атомарно: временный файл, затем переименование. Прежний файл сохраняется как `config.yaml.bak`.
- **Зачем:** мастер не должен терять пользовательские настройки (Langfuse, свои промпты, число итераций) и не должен оставлять полузаписанный конфиг.
- **Влияние:** пока только API; используется мастером.

## EN
- **What changed:** `setup/config_writer.py` builds the config from the chosen preset (Ollama models with `think: false`, `auto` language, context budget) on top of the existing file and writes it atomically: a temp file, then a rename. The previous file is kept as `config.yaml.bak`.
- **Why:** the wizard must not lose the user's own settings (Langfuse, custom prompts, iteration count) or leave a half-written config.
- **Impact:** API only; used by the wizard.
