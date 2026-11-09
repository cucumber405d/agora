# 2026-11-09 — Generator and critic agents

## RU
- **Что изменилось:** добавлены агенты Pydantic AI: генератор (свободный Markdown-текст со стримингом) и критик (типизированный вердикт `Critique`: approved, score 0–10, issues, suggestions; до 2 повторов при невалидном ответе), а также сборка входных сообщений и встроенные шаблоны инструкций.
- **Зачем:** это ядро reflection-цикла: генерация → критика → доработка.
- **Влияние:** шаблоны можно заменить своими файлами через `reflection.prompts.generator` / `reflection.prompts.critic`.

## EN
- **What changed:** added Pydantic AI agents: the generator (free Markdown text with streaming) and the critic (typed `Critique` verdict: approved, score 0–10, issues, suggestions; up to 2 retries on invalid output), plus input assembly and built-in instruction templates.
- **Why:** this is the core of the reflection loop: generate → critique → revise.
- **Impact:** templates can be replaced with custom files via `reflection.prompts.generator` / `reflection.prompts.critic`.
