# 2026-11-09 — Far-style main screen

## RU
- **Что изменилось:** главный экран TUI на Textual: слева панель файлов (отметка `Space`/`Ins`, внизу объём контекста), справа редактор промпта и лента прогона (итерации со стримингом черновика, критика со score, итог), строка статуса с моделями и состоянием Langfuse, строка F-клавиш.
- **Зачем:** консольный интерфейс в стиле Far Manager / GoldED, как задумано для проекта.
- **Влияние:** `F2` (или `Ctrl+Enter`) — запуск, `Esc` — отмена, `F10` — выход. Пустой промпт и повторный запуск во время прогона отклоняются с подсказкой. Текст моделей выводится как есть, без интерпретации разметки.

## EN
- **What changed:** Textual main screen: file panel on the left (mark with `Space`/`Ins`, context size in the footer), prompt editor and run feed on the right (iterations with streaming draft, critique with score, final answer), status line with models and Langfuse state, F-key bar.
- **Why:** a Far Manager / GoldED style console UI, as intended for the project.
- **Impact:** `F2` (or `Ctrl+Enter`) runs, `Esc` cancels, `F10` quits. An empty prompt and a second run while one is in progress are rejected with a hint. Model output is shown verbatim, markup is not interpreted.
