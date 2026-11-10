# 2026-11-10 — Copy to the system clipboard

## RU
- **Что изменилось:** копирование (`Ctrl+C` в окнах с текстом после выделения мышью, `Shift`+стрелками или `F7` — выделить всё; `F5` — итоговый ответ) теперь кладёт текст и в системный буфер обмена Windows/macOS/Linux (через `pyperclip`), а не только отправляет терминалу последовательность OSC 52. После копирования появляется уведомление «Copied N characters».
- **Зачем:** Git Bash (mintty) по умолчанию игнорирует OSC 52, и `Ctrl+C` молча ничего не копировал.
- **Влияние:** новая зависимость `pyperclip`. Если системный буфер недоступен (например, Linux без xclip/wl-copy), используется прежний путь через терминал.

## EN
- **What changed:** copying (`Ctrl+C` in text dialogs after selecting with the mouse, `Shift`+arrows or `F7` — select all; `F5` — final answer) now also puts the text on the Windows/macOS/Linux system clipboard (via `pyperclip`) instead of only sending the OSC 52 sequence to the terminal. A "Copied N characters" notification confirms it.
- **Why:** Git Bash (mintty) ignores OSC 52 by default, so `Ctrl+C` silently copied nothing.
- **Impact:** new dependency `pyperclip`. When no system clipboard is available (e.g. Linux without xclip/wl-copy), the terminal path is used as before.
