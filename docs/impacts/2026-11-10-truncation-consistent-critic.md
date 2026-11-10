# 2026-11-10 — Truncated drafts, consistent critic verdicts, no meta commentary

## RU
- **Что изменилось:**
  - Если генерация остановилась на лимите токенов/контекста (`finish_reason: length`), в ленте появляется жёлтое «⚠ draft truncated» с подсказкой, в Progress — `⚠ … truncated`, а критик получает пометку, что черновик обрезан.
  - Критик получает планку принятия («score не ниже {approve_threshold}»), пишет отзыв на языке запроса, а противоречивые вердикты отклоняются и переспрашиваются: одобрение при score ниже 5 или отказ без `issues`.
  - Генератор возвращает только ответ — без вступлений, комментариев о правках и обращений к критику; критик считает такие комментарии замечанием.
- **Зачем:** с окном Ollama 4096 токенов черновик обрывался на полуслове незаметно; критик выдавал `score 0/10 (approved)` с отзывом на немецком; генератор вставлял в ответ «Это отличный запрос! … Вот переработанный вариант».
- **Влияние:** своя инструкция критика должна учитывать новые правила согласованности. Для длинного контекста нужно увеличить окно Ollama (см. troubleshooting).

## EN
- **What changed:**
  - When generation stops at the token/context limit (`finish_reason: length`), the feed shows a yellow "⚠ draft truncated" with a hint, Progress shows `⚠ … truncated`, and the critic is told the draft was cut off.
  - The critic is given the acceptance bar ("score of at least {approve_threshold}"), writes feedback in the language of the request, and inconsistent verdicts are rejected and retried: approval with a score below 5, or rejection without `issues`.
  - The generator returns only the answer — no preamble, no comments about edits, no notes to the critic; the critic treats such comments as an issue.
- **Why:** with Ollama's 4096-token window the draft was silently cut mid-sentence; the critic returned `score 0/10 (approved)` with German feedback; the generator put "This is a great request! … Here is the revised version" into the answer.
- **Impact:** a custom critic instruction must respect the new consistency rules. Long context requires a larger Ollama window (see troubleshooting).
