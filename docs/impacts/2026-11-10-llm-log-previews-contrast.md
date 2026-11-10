# 2026-11-10 — Meaningful request previews, high-contrast text dialogs

## RU
- **Что изменилось:** в строке запроса LLM log вместо начала всегда одинаковой английской инструкции показывается суть шага: `It1: «расскажи балладу»`, `It2: revise after score 7, 6 issues`, `It2: review draft 1834 chars`. Полный текст (инструкция + вход) по-прежнему открывается по Enter. Окна с текстом — запись лога, просмотр итога (F3), конфигурация (F4) — стали контрастными: чёрный фон, белый текст, жёлтая рамка.
- **Зачем:** превью запроса не показывало, что именно ушло в модель; белый текст на бирюзовом фоне плохо читался.
- **Влияние:** инструкции моделям остаются на английском намеренно; язык ответа задаётся отдельной командой. Имена полей JSON-вердикта (`approved`, `score`, `feedback`) тоже английские — их читает программа.

## EN
- **What changed:** instead of the start of the always-identical English instruction, a request line in the LLM log shows what the step is about: `It1: «tell me a ballad»`, `It2: revise after score 7, 6 issues`, `It2: review draft 1834 chars`. The full text (instruction + input) still opens with Enter. Text dialogs — log entry, final answer viewer (F3), configuration (F4) — are high contrast: black background, white text, yellow frame.
- **Why:** the request preview did not show what actually went to the model; white text on teal was hard to read.
- **Impact:** model instructions stay in English on purpose; the answer language is set by a separate command. The JSON verdict field names (`approved`, `score`, `feedback`) are English as well — they are read by the program.
