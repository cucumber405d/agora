# 2026-11-10 — Answers and critiques in the language of the prompt

## RU
- **Что изменилось:** язык запроса определяется автоматически (русский / немецкий / английский) и явно передаётся обеим моделям: генератору — «Answer in Russian.», критику — «Write feedback, issues and suggestions in Russian.». Если ожидается русский, а отзыв критика пришёл латиницей, критика один раз просят переписать; если и повтор не по-русски, вердикт принимается как есть, а не теряется. Новая настройка `reflection.language`: `auto` (по умолчанию) или конкретный язык, например `German`.
- **Зачем:** `qwen3:14b` писал критику по-английски (и раньше по-немецки) на русский запрос: инструкции на английском перевешивали косвенное «на языке запроса».
- **Влияние:** для других языков, кроме русского, язык задаётся только инструкцией, без проверки.

## EN
- **What changed:** the request language is detected automatically (Russian / German / English) and passed explicitly to both models: "Answer in Russian." for the generator, "Write feedback, issues and suggestions in Russian." for the critic. If Russian is expected but the critic's feedback comes back in Latin script, the critic is asked once to rewrite it; if the retry is still not Russian, the verdict is kept rather than lost. New setting `reflection.language`: `auto` (default) or an explicit language such as `German`.
- **Why:** `qwen3:14b` wrote its critique in English (and earlier in German) for a Russian request: the English instructions outweighed the indirect "same language as the request".
- **Impact:** for languages other than Russian the language is set by instruction only, without a check.
