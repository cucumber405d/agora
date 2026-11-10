# 2026-11-10 — Error box keyboard control and run pre-check

## RU
- **Что изменилось:** в окне «LLM not available» работают клавиши: `←`/`→` переключают кнопки, `Enter` нажимает выбранную, `F9` сразу открывает смену моделей, `Esc` закрывает. Если последняя проверка нашла проблему, `F2` (запуск) сначала проверяет LLM заново: проблема осталась — сразу открывается окно ошибки, без обращения к модели; исправлена — прогон запускается.
- **Зачем:** окно реагировало только на мышь; запуск при неподключённой модели ждал несколько секунд повторов SDK и показывал ошибку только в ленте.
- **Влияние:** запуск по-прежнему по `F2` (или `Ctrl+Enter`); `F12` не назначена.

## EN
- **What changed:** the "LLM not available" box is keyboard-driven: `←`/`→` move between buttons, `Enter` presses the focused one, `F9` opens the model switch directly, `Esc` closes. If the last probe found a problem, `F2` (run) probes again first: if the problem persists, the error box opens immediately without calling the model; if fixed, the run starts.
- **Why:** the box reacted only to the mouse; a run with an unavailable model waited several seconds of SDK retries and showed the error only in the feed.
- **Impact:** run is still `F2` (or `Ctrl+Enter`); `F12` is not bound.
