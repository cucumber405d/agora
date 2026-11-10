# 2026-11-10 — LLM availability check with error box

## RU
- **Что изменилось:** при старте, после смены моделей (`F9`) и после `provider_error` во время прогона Agora проверяет доступность настроенных LLM и при проблеме открывает красное окно «LLM not available». В окне по ролям (Generator / Critic) указано, чего не хватает и как это исправить: Ollama не установлен или не запущен, модель не скачана (`ollama pull …`), API-ключ отсутствует или отклонён, нет связи с API. Кнопки: Retry, Models (F9), Close.
- **Зачем:** раньше без Ollama ошибка появлялась только после первого запуска строкой `provider_error: Connection error.` без подсказки.
- **Влияние:** проверка идёт в фоне (таймаут 3 с на endpoint, одинаковые endpoint проверяются один раз) и не блокирует интерфейс; для облачных провайдеров выполняется бесплатный запрос списка моделей или ключа. Новая явная зависимость: `httpx`.

## EN
- **What changed:** at start-up, after switching models (`F9`) and after a `provider_error` during a run, Agora probes the configured LLMs and opens a red "LLM not available" box on problems. Per role (Generator / Critic) it shows what is missing and how to fix it: Ollama not installed or not running, model not pulled (`ollama pull …`), API key missing or rejected, no connection to the API. Buttons: Retry, Models (F9), Close.
- **Why:** previously, without Ollama the error appeared only after the first run as `provider_error: Connection error.` with no hint.
- **Impact:** the probe runs in the background (3 s timeout per endpoint, identical endpoints are probed once) and does not block the UI; for cloud providers it makes a free models/key request. New explicit dependency: `httpx`.
