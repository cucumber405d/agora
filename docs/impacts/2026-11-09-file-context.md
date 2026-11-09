# 2026-11-09 — File context source

## RU
- **Что изменилось:** локальные файлы загружаются в контекст агента с проверкой расширения, размера (`max_file_kb`), кодировки UTF-8 и общего бюджета токенов (`max_total_tokens`, считается накопительно в порядке выбора).
- **Зачем:** пользователь отмечает файлы в панели, как в Far, и их содержимое уходит в запрос.
- **Влияние:** неподходящие файлы (бинарные, не UTF-8, слишком большие, сверх бюджета) пропускаются с указанием причины, а не роняют приложение. Токены оцениваются приблизительно: символы / 4.

## EN
- **What changed:** local files are loaded into the agent context with checks for extension, size (`max_file_kb`), UTF-8 encoding and a cumulative token budget (`max_total_tokens`, applied in selection order).
- **Why:** the user marks files in a Far-style panel and their content goes into the request.
- **Impact:** unsuitable files (binary, non-UTF-8, too large, over budget) are skipped with a reason instead of crashing the app. Tokens are estimated as characters / 4.
