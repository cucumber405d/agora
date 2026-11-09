# 2026-11-09 — TUI dialogs and actions

## RU
- **Что изменилось:** добавлены `F1` справка, `F3` просмотр итога в Markdown, `F4` текущая конфигурация (только чтение), `F5` копирование итога, `F6` сохранение прогона в `./agora-runs/<время>.md` (итог + история итераций), `F9` смена моделей и температур. Клавиши в нижней строке идут по порядку F1…F10, как в Far.
- **Зачем:** привычный Far-сценарий работы с результатом без выхода из приложения.
- **Влияние:** изменения из `F9` действуют только в текущей сессии, YAML не перезаписывается; если для новой модели нет API-ключа, остаются прежние модели и показывается ошибка. Пока нет результата, `F3`/`F5`/`F6` сообщают «Nothing to copy/save yet». Пока открыт диалог, `F2` не запускает прогон, `Esc` закрывает диалог.

## EN
- **What changed:** added `F1` help, `F3` Markdown viewer for the final answer, `F4` read-only active configuration, `F5` copy the final answer, `F6` save the run to `./agora-runs/<timestamp>.md` (final answer + iteration history), `F9` model and temperature switch. The footer lists keys in F1…F10 order, as in Far.
- **Why:** the familiar Far workflow for handling results without leaving the app.
- **Impact:** `F9` changes apply to the current session only; the YAML is never rewritten. If the new model has no API key, the previous models stay and an error is shown. Without a result, `F3`/`F5`/`F6` report "Nothing to copy/save yet". While a dialog is open, `F2` does not start a run and `Esc` closes the dialog.
