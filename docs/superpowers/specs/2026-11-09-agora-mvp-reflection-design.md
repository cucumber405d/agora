# Agora MVP — reflection-агент с TUI в стиле Far

- **Дата:** 2026-11-09
- **Статус:** реализовано (MVP, ветка `feat/mvp`); ручной smoke на Windows и интеграционный тест с Ollama — за пользователем
- **Цикл:** 1 из 5 (MVP)
- **Пакет:** `ibikus.appa.agora`

## 1. Цель

Agora — agentic- и мультиагентный модуль платформы Appa. Первый цикл покрывает только ядро:
**reflection-агент** отвечает на промпт пользователя с учётом подключённого контекста. Модель-*генератор*
с высокой температурой пишет черновик, модель-*критик* с низкой температурой (та же или другая)
его оценивает. Цикл повторяется, пока критик не одобрит черновик или пока не кончится лимит итераций.
Всё настраивается через конфиг.

Приложение — **текстовое консольное в стиле Far Manager / GoldED** (TUI на Textual).

Проект одновременно портфолио, поэтому чистые слои, тесты, CI и docs-as-code входят в объём.

### Roadmap (вне объёма этой spec, на каждый цикл — своя spec)

1. **MVP** (эта spec): reflection-цикл, конфиг, TUI, трейсинг в Langfuse, тесты
2. RAG + ChromaDB как источник контекста
3. Memory layer (PostgreSQL), история сессий
4. Tool calling / MCP
5. Слой FastAPI, Docker/K8s, мультиагентные сценарии

## 2. Решения

| Тема | Решение |
|---|---|
| UI | Textual TUI, вид Far/GoldED (синяя тема, панели, строка F-клавиш) |
| Язык UI и комментариев в коде | английский |
| LLM-провайдеры | настраиваются для каждой роли отдельно: Ollama (локально), Anthropic, OpenAI, OpenRouter |
| Критерий остановки | структурированный вердикт `Critique`: `approved` или `score >= threshold`, но не больше `max_iterations` |
| Контекст | промпт + локальные файлы, выбранные в файловой панели в духе Far |
| Observability | Langfuse, self-hosted через `docker compose`; опционально (нет ключей → no-op) |
| Оркестрация | LangGraph `StateGraph`; каждый узел — обёртка над агентом Pydantic AI |

## 3. Архитектура

Зависимости идут только вниз. Ядро ничего не знает про UI.

```
src/ibikus/appa/agora/
├── config/        # pydantic-settings: AppConfig, ModelConfig, ReflectionConfig; загрузка YAML + .env
├── llm/           # фабрика моделей: ModelConfig -> pydantic_ai Model (ollama/anthropic/openai/openrouter)
├── agents/        # generator.py, critic.py (агенты Pydantic AI); шаблоны промптов
├── reflection/    # state.py (ReflectionState), graph.py (StateGraph), events.py (RunEvent), service.py
├── context/       # протокол ContextSource; FileContextSource (лимиты размера/токенов, расширения)
├── observability/ # инициализация Langfuse; no-op, если не настроен
├── tui/           # приложение Textual: экраны, панели, keybindings, .tcss
└── __main__.py    # `agora [--config PATH]`
tests/  docs/  config/agora.yaml  prompts/  docker/langfuse/compose.yaml  pyproject.toml
```

### 3.1 Модель данных

- `ModelConfig`: `provider`, `name`, `temperature`, `max_tokens`, `base_url?`. API-ключи — только из env.
- `ReflectionConfig`: `generator: ModelConfig`, `critic: ModelConfig`, `max_iterations`, `approve_threshold`, пути к промптам.
- `Critique` (тип вывода критика): `approved: bool`, `score: int (0..10)`, `issues: list[str]`, `suggestions: list[str]`.
- `ReflectionState`: `prompt`, `context`, `iteration`, `drafts[]`, `critiques[]`, `final`, `status`.
- `RunEvent` (discriminated union): `IterationStarted`, `DraftChunk`, `DraftDone`, `CritiqueDone`, `RunFinished`, `RunFailed`.

### 3.2 Сервис-фасад

`ReflectionService.run(prompt: str, context: Context) -> AsyncIterator[RunEvent]` — единственная
точка входа в ядро. Сейчас его вызывает TUI, в цикле 5 — FastAPI.

### 3.3 Инструменты

Python 3.12, `uv`, `ruff` (lint + format), `pytest` + `pytest-asyncio`, `mypy --strict` для пакетов
ядра, CI на GitHub Actions.

## 4. Reflection-граф

```
generate --> critique --> route
   ^                        |
   |-- не одобрено, iter < max
                            |-- approved или score >= threshold --> finalize (status=approved)
                            |-- iter >= max_iterations          --> finalize (status=max_iterations)
```

- **generate.** На итерации 1 на вход идут системный промпт, контекст (каждый файл под
  заголовком `### file: <path>`) и запрос пользователя. Начиная с итерации 2 добавляются
  предыдущий черновик и его критика с инструкцией доработать черновик по замечаниям.
  Токены стримятся событиями `DraftChunk`.
- **critique.** Критик видит запрос, контекст и черновик и обязан вернуть `Critique`.
  Output retries Pydantic AI: 2.
- **finalize.** При `approved` результат — последний черновик. При `max_iterations` — черновик
  с **наибольшим score** (при равенстве — более поздний).
- **События.** Узлы отправляют `RunEvent` через custom stream mode LangGraph. Сервис отдаёт их
  наружу как async-итератор.
- **Отмена.** Esc отменяет asyncio-task; сервис отправляет `RunFailed(reason="cancelled")`.
- **Langfuse.** Один trace на прогон, на каждую итерацию — span на фазу (`iteration-N/generate`,
  `iteration-N/critique`; span не может пересечь два узла LangGraph), одна generation на каждый
  вызов модели. Метаданные: модель, температура, score, approved.

## 5. TUI (Textual)

```
┌ Files ─────────────────┐┌ Prompt ────────────────────────────────────────┐
│ ..                     ││ Explain the difference between ...             │
│ [x] docs/notes.md      ││                                                │
│ [ ] src/main.py        │├ Run ─ iter 2/3 ─ score 6 → 8 ─────────────────┤
│ [x] spec.txt           ││ ▸ Iter 1  draft  ▸ critique (score 6)          │
│                        ││ ▾ Iter 2  draft (streaming...)                 │
│ Context: 2 files, 3.1k ││   ... █                                        │
└────────────────────────┘└────────────────────────────────────────────────┘
 Gen: ollama/qwen2.5 t=0.9 │ Critic: anthropic/claude-haiku t=0.1 │ Langfuse ●
 F1 Help F2 Run F3 View F4 Config F5 Copy F6 Save F9 Models F10 Quit  Esc Cancel
```

Все надписи интерфейса — на английском.

- **Панель файлов:** браузер с корнем в рабочей директории. `Space`/`Ins` отмечает файл.
  Внизу видны число файлов и оценка токенов контекста.
- **Редактор промпта:** многострочный. Прогон запускается по `Ctrl+Enter` или `F2`.
- **Лента прогона:** по сворачиваемому блоку на итерацию, в нём стримящийся черновик и критика
  (score, issues). Итоговый ответ подсвечен.
- **Статус-строка:** активные модели, их температуры и состояние Langfuse.
- **Клавиши:** `F1` справка · `F2` запуск · `F3` полноэкранный Markdown-просмотр итога ·
  `F4` просмотр конфига (только чтение) · `F5` копировать итог · `F6` сохранить итог вместе
  с историей итераций в Markdown · `F9` диалог моделей и температур (только на сессию, YAML
  не перезаписывается) · `F10` выход · `Esc` отмена прогона.
- Классическая синяя тема Far в `.tcss`. Работает в Windows Terminal и WSL2. Мышь поддерживается,
  но любое действие доступно с клавиатуры.

## 6. Конфигурация

Приоритет (от высшего к низшему): env `AGORA_*` (вложенные поля через `__`) > файл из `--config` >
`AGORA_CONFIG` > `./config/agora.yaml` > встроенные дефолты.
Секреты (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `LANGFUSE_*`) читаются только
из env или `.env`, никогда из YAML.

```yaml
reflection:
  max_iterations: 3
  approve_threshold: 8
  generator: { provider: ollama, name: qwen2.5:7b, temperature: 0.9, base_url: http://localhost:11434/v1 }
  critic:    { provider: anthropic, name: claude-haiku-4-5, temperature: 0.1 }
  prompts:   { generator: prompts/generator.md, critic: prompts/critic.md }
context: { max_file_kb: 256, max_total_tokens: 32000, allowed_ext: [.md, .txt, .py, .java, .yaml, .json] }
observability: { langfuse: { enabled: auto } }   # auto = включено, если есть ключи
```

## 7. Обработка ошибок

| Ситуация | Поведение |
|---|---|
| Невалидный конфиг | понятная ошибка pydantic с именем поля; выводится до старта TUI; exit code 2 |
| Провайдер недоступен / таймаут / 429 | 3 ретрая с backoff, затем `RunFailed` в ленте; приложение продолжает работать |
| Невалидный вывод критика | output retries, затем `RunFailed(reason="critic_invalid")` |
| Контекст превышает лимит | предупреждение в панели файлов; файлы сверх лимита не отправляются |
| Langfuse недоступен | только warning в лог; на работу не влияет |
| Логирование | `~/.agora/logs/agora.log` (никогда не в stdout, чтобы не ломать TUI) |

## 8. Тестирование (TDD)

- **Unit:** загрузка конфига, переопределение через env, валидация; фабрика моделей; сборка
  промптов; лимиты и расширения `FileContextSource`; роутинг графа.
- **Граф:** прогон на `pydantic_ai.models.test.TestModel` / `FunctionModel`, без сети.
  Сценарии: одобрено на итерации 1; улучшение до порога; исчерпание лимита с выбором лучшего
  черновика; невалидный вывод критика; отмена.
- **TUI:** Textual `App.run_test()` + `Pilot` (отметить файл, ввести промпт, нажать F2,
  проверить события в ленте); snapshot-тесты через `pytest-textual-snapshot`.
- **Интеграционные:** тесты с реальным Ollama помечены `@pytest.mark.integration`, по умолчанию
  пропускаются.
- **CI:** `ruff check`, `ruff format --check`, `mypy`, `pytest` на GitHub Actions.

## 9. Конвенции проекта

- **Языки:** UI и комментарии в коде — английский; specs и планы — русский; брифы — английский.
- **Docs as code:** `docs/start.md` (команды сборки и запуска), `docs/architecture.md`,
  `docs/configuration.md`, `docs/troubleshooting.md`.
- **Impacts:** каждая фича, фикс или баг получает запись в `docs/impacts/` на **русском и
  английском**. Один файл на изменение: `docs/impacts/YYYY-MM-DD-<slug>.md`, разделы `## RU`
  и `## EN`; в каждом — *что изменилось*, *зачем* и *влияние* (что заметно пользователю,
  изменения конфига, заметки по миграции).

## 10. Вне объёма (YAGNI)

RAG, память между сессиями, tools/MCP, FastAPI, K8s, хранение сессий в БД, редактирование YAML
из TUI.
