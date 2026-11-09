# 2026-11-09 — Provider-agnostic model factory

## RU
- **Что изменилось:** фабрика моделей строит модель Pydantic AI из `ModelConfig` для Ollama, Anthropic, OpenAI и OpenRouter; температура, таймаут и ретраи SDK задаются в настройках вызова.
- **Зачем:** генератор и критик настраиваются независимо — любая комбинация локальной и облачной модели.
- **Влияние:** отсутствующий API-ключ или недопустимое имя модели (для OpenRouter обязателен префикс, например `openai/gpt-4o-mini`) дают понятную ошибку конфигурации ещё до старта.

## EN
- **What changed:** the model factory builds a Pydantic AI model from `ModelConfig` for Ollama, Anthropic, OpenAI and OpenRouter; temperature, timeout and SDK retries go into the per-call settings.
- **Why:** generator and critic are configured independently — any mix of local and cloud models.
- **Impact:** a missing API key or an invalid model name (OpenRouter requires a vendor prefix, e.g. `openai/gpt-4o-mini`) produces a clear configuration error before start-up.
