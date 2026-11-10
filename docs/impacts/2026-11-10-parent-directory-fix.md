# 2026-11-10 — Fix: going to the parent directory

## RU
- **Что изменилось:** в начале панели файлов появилась строка `..`, как в Far: Enter или клик по ней поднимает на уровень выше (на корне диска её нет, отметить её нельзя). `Ctrl+PgUp` теперь работает из любого места, в том числе когда фокус в поле промпта. `Backspace` поднимает наверх только в панели файлов, в промпте он по-прежнему стирает символ.
- **Зачем:** подняться было нельзя: после запуска фокус стоит в промпте, и `Ctrl+PgUp`/`Backspace` до панели не доходили; мышью перехода не было вовсе.
- **Влияние:** справка F1 и `docs/start.md` обновлены.

## EN
- **What changed:** the file panel starts with a `..` entry, as in Far: Enter or a click on it goes one level up (absent at the drive root, cannot be marked). `Ctrl+PgUp` now works from anywhere, including when the prompt has focus. `Backspace` goes up only in the file panel; in the prompt it still deletes a character.
- **Why:** going up was impossible: after start-up the prompt has focus, so `Ctrl+PgUp`/`Backspace` never reached the panel, and there was no way to do it with the mouse.
- **Impact:** F1 help and `docs/start.md` updated.
