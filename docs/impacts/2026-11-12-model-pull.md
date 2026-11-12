# 2026-11-12 — Pulling models

## RU
- **Что изменилось:** `setup/models.py` определяет, каких моделей выбранной конфигурации не хватает (`llama3` и `llama3:latest` считаются одной моделью), скачивает их через `/api/pull` с прогрессом и проверяет результат: короткий запрос к генератору и `ollama ps` (100% GPU, окно контекста не меньше нужного). Ошибка внутри потока Ollama (например, нет такой модели) и обрыв без `success` — это ошибка, а не успех.
- **Зачем:** пользователь не должен скачивать модели вручную в консоли.
- **Влияние:** пока только API; используется мастером. Отмена прерывает поток, при следующем запуске Ollama продолжает с места обрыва.

## EN
- **What changed:** `setup/models.py` finds which models of the chosen preset are missing (`llama3` and `llama3:latest` count as one), pulls them via `/api/pull` with progress and verifies the result: a short request to the generator plus `ollama ps` (100% GPU, a large enough context window). An error inside Ollama's stream (e.g. an unknown model) or a stream ending without `success` is a failure, not a success.
- **Why:** users should not have to pull models by hand in a console.
- **Impact:** API only; used by the wizard. Cancelling stops the stream; Ollama resumes from where it stopped on the next pull.
