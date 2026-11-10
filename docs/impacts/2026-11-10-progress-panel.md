# 2026-11-10 — Progress panel

## RU
- **Что изменилось:** под панелью файлов появилась панель «Progress», как информационная панель в Far (`Ctrl+L` — скрыть/показать). В заголовке — вращающийся индикатор и время прогона (по окончании `✓`, `✕` или `■`), ниже — полоса прогресса (шаги «генератор + критик» × `max_iterations`, при раннем одобрении сразу 100%) и журнал стадий со временем от старта: контекст, генерация (≈токены, длительность, токены/с), критика (score, ✓/✗, длительность), итог или ошибка.
- **Зачем:** во время долгих локальных прогонов не было видно, что происходит и сколько осталось.
- **Влияние:** ядро не менялось — панель строится из тех же событий прогона, что и лента.

## EN
- **What changed:** a "Progress" panel under the file panel, like Far's info panel (`Ctrl+L` shows/hides it). The title shows a spinner and the run time (`✓`, `✕` or `■` when finished); below are a progress bar (generator + critic steps × `max_iterations`, 100% at once on early approval) and a stage log with times from the start: context, generation (≈tokens, duration, tokens/s), critique (score, ✓/✗, duration), result or error.
- **Why:** during long local runs there was no indication of what was happening or how much was left.
- **Impact:** the core is unchanged — the panel is built from the same run events as the feed.
