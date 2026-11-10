# 2026-11-10 — Robust critic for small local models

## RU
- **Что изменилось:**
  - Вердикт критика запрашивается как ответ по JSON-схеме (`response_format: json_schema`), а не через вызов инструмента: Ollama и облачные провайдеры не дают модели выйти за схему, поэтому `approved` и `score` присутствуют всегда.
  - Замечания, которые лишь повторяют сообщения валидации («Field 'approved' is required»), отклоняются и не попадают генератору.
  - Если критик всё же не смог выдать вердикт, прогон больше не обрывается ошибкой `critic_invalid`: в ленте появляется жёлтое «critique failed: …», а итогом становится последний черновик со статусом `critic_failed` (доступен по F3/F5/F6).
- **Зачем:** с `qwen2.5:7b` критик возвращал пустую оценку 0, копировал тексты ошибок в замечания или отвечал Markdown-текстом, и весь прогон терялся.
- **Влияние:** статус `critic_invalid` заменён на `RunResult.status = "critic_failed"`. Для лучшей критики рекомендуется отдельная, более сильная модель критика.

## EN
- **What changed:**
  - The critic's verdict is requested as a JSON-schema constrained response (`response_format: json_schema`) instead of a tool call: Ollama and the cloud providers keep the model inside the schema, so `approved` and `score` are always present.
  - Issues that merely echo validation messages ("Field 'approved' is required") are rejected and never reach the generator.
  - If the critic still cannot produce a verdict, the run no longer aborts with `critic_invalid`: the feed shows a yellow "critique failed: …" and the latest draft becomes the result with status `critic_failed` (available via F3/F5/F6).
- **Why:** with `qwen2.5:7b` the critic returned an empty score 0, copied error texts into the issues or answered in Markdown prose, and the whole run was lost.
- **Impact:** the `critic_invalid` failure is replaced by `RunResult.status = "critic_failed"`. A separate, stronger critic model is recommended for better critiques.
