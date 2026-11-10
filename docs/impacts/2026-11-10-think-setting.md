# 2026-11-10 — `think` setting for Ollama thinking models

## RU
- **Что изменилось:** у модели в конфиге появилась настройка `think` (только для Ollama): `think: false` отключает фазу скрытых размышлений у моделей вроде `qwen3` и `qwen3.5` (в запрос уходит `reasoning_effort: "none"`, проверено на Ollama). Если генератор не выдал ответа, прогон заканчивается понятной ошибкой `generator_failed` с подсказкой вместо `internal`. В панели Progress генерация показывает `waiting…`, пока не придёт первый токен ответа.
- **Зачем:** `qwen3.5:9b` 51 секунду размышляла, израсходовала весь лимит контекста и не написала ответа; в интерфейсе это выглядело как зависание и `internal: UnexpectedModelBehavior`.
- **Влияние:** для моделей с размышлениями рекомендуется `think: false` у обеих ролей. Без настройки поведение прежнее.

## EN
- **What changed:** model config has a new `think` setting (Ollama only): `think: false` disables the hidden reasoning phase of models such as `qwen3` and `qwen3.5` (the request carries `reasoning_effort: "none"`, verified against Ollama). If the generator produces no answer, the run ends with a clear `generator_failed` error and a hint instead of `internal`. In the Progress panel the generation shows `waiting…` until the first answer token arrives.
- **Why:** `qwen3.5:9b` reasoned for 51 seconds, used up the whole context and wrote no answer; the UI looked frozen and ended with `internal: UnexpectedModelBehavior`.
- **Impact:** `think: false` is recommended for both roles with thinking models. Without the setting, behaviour is unchanged.
