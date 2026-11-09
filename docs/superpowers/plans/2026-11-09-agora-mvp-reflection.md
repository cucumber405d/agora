# Agora MVP — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Цель:** консольное приложение `agora`. Reflection-агент (генератор + критик) отвечает на промпт с учётом выбранных файлов, интерфейс — TUI в стиле Far.

**Архитектура:** слои `config → llm → context → agents → reflection → observability → tui`, зависимости только вниз. Цикл generate/critique — это LangGraph `StateGraph`, узлы вызывают агентов Pydantic AI. Ядро отдаёт наружу только `ReflectionService.run(...) -> AsyncIterator[RunEvent]`.

**Стек (версии проверены 2026-11-09):** Python ≥ 3.12, uv, `pydantic-ai-slim[openai,anthropic]==2.66.*`, `langgraph==1.2.*`, `textual==8.2.*`, `langfuse==5.2.*`, `pydantic-settings[yaml]==2.16.*`, `python-dotenv`, dev: `pytest`, `pytest-asyncio==1.4.*`, `pytest-textual-snapshot==1.1.*`, `ruff==0.17.*`, `mypy==2.4.*`.

**Spec:** `docs/superpowers/specs/2026-11-09-agora-mvp-reflection-design.md`

## Global Constraints

- Корневой пакет `ibikus.appa.agora`: `src/ibikus/` и `src/ibikus/appa/` — namespace-пакеты (без `__init__.py`), у `src/ibikus/appa/agora/` есть `__init__.py`.
- Тексты UI, комментарии, docstrings, сообщения коммитов — на английском. Брифы субагентам — на английском.
- **Impacts:** каждая задача (фича/фикс) добавляет `docs/impacts/2026-11-09-<slug>.md` с разделами `## RU` и `## EN`, в каждом три пункта: *What changed / Что изменилось*, *Why / Зачем*, *Impact / Влияние*. Файл входит в коммит задачи. Формат — как в `docs/impacts/2026-11-09-mvp-design.md`.
- `PYDANTIC_AI_NO_BANNER=1` выставляется через `os.environ.setdefault` в `ibikus/appa/agora/__init__.py` до любого импорта `pydantic_ai`: Pydantic AI 2.x печатает баннер в stdout и ломает TUI. Для тестов то же самое делает `tests/conftest.py`.
- Ничего не пишем в stdout/stderr, пока работает TUI. Логи идут в `$AGORA_HOME/logs/agora.log`, где `AGORA_HOME` по умолчанию `~/.agora`.
- Секреты только из env/`.env`: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`. В конфиг-моделях нет полей для ключей (`extra="forbid"`).
- Дефолты из spec: `max_iterations=3`, `approve_threshold=8`, генератор `ollama/qwen2.5:7b t=0.9 base_url=http://localhost:11434/v1`, критик `anthropic/claude-haiku-4-5 t=0.1`, `max_file_kb=256`, `max_total_tokens=32000`, `allowed_ext=[.md,.txt,.py,.java,.yaml,.json]`, Langfuse `enabled=auto`.
- Тесты не ходят в сеть. Реальные модели — только под `@pytest.mark.integration`, по умолчанию `-m "not integration"`.
- Каждая задача завершается зелёными `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest`.

## Review Focus

1. **Пустой промпт + F2.** Ожидание: прогон не стартует, `notify("Prompt is empty")`; сервис на пустой/пробельный промпт сразу отдаёт `RunFailed(reason="invalid_input")`. Тесты — задачи 6 и 8.
2. **Отмеченный бинарный или не-UTF-8 файл** (например `.json` в cp1251). Ожидание: файл пропускается с `reason="not_utf8"`, приложение не падает. Тест — задача 3.
3. **Повторный F2 во время прогона.** Ожидание: второй прогон не стартует, `notify("A run is already in progress")`. Тест — задача 8.
4. **Ollama не запущен / нет сети.** Ожидание: `RunFailed(reason="provider_error")` с понятным текстом в ленте, без traceback на экране. Тест — задача 6 (`FunctionModel`, бросающий `ModelAPIError`).
5. **F5/F6 до первого результата.** Ожидание: `notify("Nothing to copy/save yet")`, файл не создаётся. Тест — задача 9.

---

## Структура файлов

```
pyproject.toml  .gitignore  .env.example  config/agora.yaml
src/ibikus/appa/agora/
  __init__.py                 # banner env, __version__
  __main__.py                 # main(argv) -> int
  logging_setup.py            # setup_logging(home: Path) -> Path
  config/__init__.py          # re-export
  config/models.py            # ModelConfig, PromptsConfig, ReflectionConfig, ContextConfig, LangfuseConfig, ObservabilityConfig, AppConfig
  config/loader.py            # load_config, ConfigError
  llm/factory.py              # build_model, build_settings, describe, required_env_key
  context/models.py           # ContextFile, SkippedFile, Context, estimate_tokens
  context/files.py            # ContextSource (Protocol), FileContextSource
  agents/templates/generator.md, critic.md
  agents/prompts.py           # load_instructions, render_context, build_generator_input, build_critic_input
  agents/critic.py            # Critique, build_critic
  agents/generator.py         # build_generator
  reflection/events.py        # RunEvent union + RunResult, IterationRecord
  reflection/state.py         # ReflectionState
  reflection/graph.py         # Agents, is_approved, route, select_final, build_graph, CriticInvalidError
  reflection/service.py       # ReflectionService
  reflection/export.py        # render_run_markdown
  observability/langfuse.py   # Observability, NoopObservability, LangfuseObservability, setup_observability
  tui/app.py                  # AgoraApp
  tui/files_panel.py          # FilesPanel
  tui/run_feed.py             # RunFeed
  tui/status_bar.py           # StatusBar
  tui/dialogs.py              # HelpScreen, ViewerScreen, ConfigScreen, ModelsScreen
  tui/agora.tcss
tests/ (зеркалит src: tests/config, tests/llm, ...), tests/conftest.py
docker/langfuse/compose.yaml  .github/workflows/ci.yml
docs/start.md docs/architecture.md docs/configuration.md docs/troubleshooting.md
```

---

### Task 1: каркас проекта и конфигурация

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `config/agora.yaml`, `src/ibikus/appa/agora/__init__.py`, `src/ibikus/appa/agora/config/{__init__,models,loader}.py`, `tests/conftest.py`, `tests/config/test_loader.py`, `docs/start.md`, `docs/impacts/2026-11-09-project-scaffold-config.md`

**Interfaces:**
- Produces:
  - `Provider = Literal["ollama", "anthropic", "openai", "openrouter"]`
  - `ModelConfig(BaseModel, extra="forbid")`: `provider: Provider`, `name: str`, `temperature: float = Field(ge=0, le=2)`, `max_tokens: int | None = None`, `base_url: str | None = None`, `timeout_s: float = 60`, `max_retries: int = 3`
  - `PromptsConfig`: `generator: Path | None = None`, `critic: Path | None = None` (`None` → встроенный шаблон)
  - `ReflectionConfig`: `max_iterations: int = Field(3, ge=1, le=10)`, `approve_threshold: int = Field(8, ge=0, le=10)`, `generator: ModelConfig`, `critic: ModelConfig`, `prompts: PromptsConfig`
  - `ContextConfig`: `max_file_kb: int = 256`, `max_total_tokens: int = 32000`, `allowed_ext: list[str]`
  - `LangfuseConfig`: `enabled: Literal["auto", "on", "off"] = "auto"`; `ObservabilityConfig`: `langfuse: LangfuseConfig`
  - `AppConfig(BaseSettings)`: `reflection`, `context`, `observability`; `env_prefix="AGORA_"`, `env_nested_delimiter="__"`, `extra="forbid"`
  - `load_config(path: Path | None = None, env: Mapping[str, str] | None = None, cwd: Path | None = None) -> AppConfig`
  - `class ConfigError(Exception)` — `str(e)` перечисляет ошибки в виде `"<dotted.field>: <msg>"`, по одной на строку

- [ ] **Step 1: pyproject и инструменты.** `pyproject.toml`: build backend `hatchling`, `[tool.hatch.build.targets.wheel] packages = ["src/ibikus"]`, script `agora = "ibikus.appa.agora.__main__:main"`, зависимости из шапки. `[tool.ruff] line-length = 100`, `target-version = "py312"`, lint `select = ["E","F","I","UP","B","SIM","ASYNC","RUF"]`. `[tool.mypy] strict = true`, `packages = ["ibikus.appa.agora"]`, `mypy_path = "src"`, `explicit_package_bases = true`. `[tool.pytest.ini_options] asyncio_mode = "auto"`, `testpaths = ["tests"]`, `addopts = "-m 'not integration'"`, `markers = ["integration: needs real LLM"]`. `.gitignore`: `.venv/ __pycache__/ .env .mypy_cache/ .pytest_cache/ .ruff_cache/ agora-runs/ dist/`. `.env.example` — все шесть ключей с пустыми значениями. `uv sync` проходит.

- [ ] **Step 2: failing-тесты конфига** в `tests/config/test_loader.py` (каждый тест работает в `tmp_path`, `env={}` передаётся явно):

```python
def test_defaults_when_no_file(tmp_path):
    cfg = load_config(env={}, cwd=tmp_path)
    assert cfg.reflection.max_iterations == 3
    assert cfg.reflection.approve_threshold == 8
    assert (cfg.reflection.generator.provider, cfg.reflection.generator.name) == (
        "ollama",
        "qwen2.5:7b",
    )
    assert cfg.reflection.generator.temperature == 0.9
    assert (
        cfg.reflection.critic.provider == "anthropic" and cfg.reflection.critic.temperature == 0.1
    )
    assert cfg.context.allowed_ext == [".md", ".txt", ".py", ".java", ".yaml", ".json"]
    assert cfg.observability.langfuse.enabled == "auto"


def test_explicit_path_wins_over_agora_config_env_and_cwd(tmp_path):
    ...
    # cwd/config/agora.yaml: max_iterations 4; file from AGORA_CONFIG: 5; explicit path: 6 -> 6
    # без explicit -> 5; без AGORA_CONFIG -> 4


def test_env_overrides_yaml(tmp_path):
    # yaml: reflection.critic.temperature 0.3; env AGORA_REFLECTION__CRITIC__TEMPERATURE=0.2
    assert cfg.reflection.critic.temperature == 0.2


def test_api_key_in_yaml_is_rejected(tmp_path):
    # yaml: reflection.critic.api_key: "x"
    with pytest.raises(ConfigError, match=r"reflection\.critic\.api_key"):
        ...


def test_invalid_value_names_field(tmp_path):
    # yaml: reflection.approve_threshold: 11
    with pytest.raises(ConfigError, match=r"reflection\.approve_threshold"):
        ...


def test_missing_explicit_file_raises(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml", env={})
```

- [ ] **Step 3: проверить, что тесты падают.** `uv run pytest tests/config -v` → FAIL (ImportError).

- [ ] **Step 4: реализовать `config/models.py` и `config/loader.py`.** YAML подключается через `settings_customise_sources`, который возвращает `(env_settings, YamlConfigSettingsSource(settings_cls, yaml_file=_yaml_path.get()))`. Путь передаётся через module-level `ContextVar[Path | None]`, его выставляет `load_config`. Порядок: env выше YAML. `env` из аргумента подаётся через `env_settings`, без чтения `os.environ`; если `env is None`, используется `os.environ`. `ValidationError` превращается в `ConfigError` по `e.errors()` (`".".join(map(str, loc))`). `tests/conftest.py`: `os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")`. `__init__.py` пакета: то же плюс `__version__ = "0.1.0"`.

- [ ] **Step 5: прогнать тесты.** `uv run pytest tests/config -v` → PASS.

- [ ] **Step 6: `config/agora.yaml` (повторяет дефолты spec, раздел 6, без `prompts`; закомментированный пример `prompts:`) и `docs/start.md`** (англ.: `uv sync`, `cp .env.example .env`, `uv run agora`, `uv run pytest`, `uv run ruff check .`, `uv run mypy src`). Тест `test_repo_config_file_is_valid`: `load_config(Path("config/agora.yaml"), env={})` не падает.

- [ ] **Step 7: полный гейт + impact + commit.**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest
git add -A && git commit -m "feat(config): project scaffold and layered YAML/env configuration"
```

---

### Task 2: фабрика моделей

**Files:** Create `src/ibikus/appa/agora/llm/{__init__,factory}.py`, `tests/llm/test_factory.py`, impact `2026-11-09-model-factory.md`

**Interfaces:**
- Consumes: `ModelConfig`, `ConfigError` (Task 1)
- Produces:
  - `required_env_key(provider: Provider) -> str | None` — `{"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}`, у ollama `None`
  - `build_model(cfg: ModelConfig, env: Mapping[str, str] | None = None) -> pydantic_ai.models.Model`
  - `build_settings(cfg: ModelConfig) -> ModelSettings` — `temperature`, `timeout=cfg.timeout_s`, `max_retries=cfg.max_retries`, `max_tokens` только если задан
  - `describe(cfg: ModelConfig) -> str` → `"ollama/qwen2.5:7b t=0.9"`

- [ ] **Step 1: failing-тесты**

```python
def test_ollama_model_uses_base_url():
    m = build_model(ModelConfig(provider="ollama", name="qwen2.5:7b", temperature=0.9,
                                base_url="http://h:1/v1"), env={})
    assert isinstance(m, OllamaModel) and m.model_name == "qwen2.5:7b"
    assert str(m.client.base_url).startswith("http://h:1/v1")

def test_ollama_default_base_url():  # base_url=None -> http://localhost:11434/v1

@pytest.mark.parametrize("provider,cls,key", [("anthropic", AnthropicModel, "ANTHROPIC_API_KEY"),
    ("openai", OpenAIChatModel, "OPENAI_API_KEY"), ("openrouter", OpenRouterModel, "OPENROUTER_API_KEY")])
def test_cloud_models(provider, cls, key):
    assert isinstance(build_model(ModelConfig(provider=provider, name="m", temperature=0.1), env={key: "k"}), cls)

def test_missing_key_raises_config_error():
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY is not set"):
        build_model(ModelConfig(provider="anthropic", name="m", temperature=0.1), env={})

def test_settings():
    s = build_settings(ModelConfig(provider="ollama", name="x", temperature=0.9))
    assert s["temperature"] == 0.9 and s["max_retries"] == 3 and s["timeout"] == 60 and "max_tokens" not in s

def test_describe():
    assert describe(ModelConfig(provider="ollama", name="qwen2.5:7b", temperature=0.9)) == "ollama/qwen2.5:7b t=0.9"
```

- [ ] **Step 2:** `uv run pytest tests/llm -v` → FAIL.
- [ ] **Step 3: реализовать `factory.py`.** Классы: `OllamaModel` + `OllamaProvider(base_url=...)`, `AnthropicModel` + `AnthropicProvider(api_key=...)`, `OpenAIChatModel` + `OpenAIProvider(api_key=..., base_url=cfg.base_url)`, `OpenRouterModel` + `OpenRouterProvider(api_key=...)`. Ключ берётся из `env` (по умолчанию `os.environ`) и передаётся провайдеру явно.
- [ ] **Step 4:** `uv run pytest tests/llm -v` → PASS.
- [ ] **Step 5: гейт + impact + commit** `feat(llm): provider-agnostic model factory`.

---

### Task 3: контекст из файлов

**Files:** Create `src/ibikus/appa/agora/context/{__init__,models,files}.py`, `tests/context/test_files.py`, impact `2026-11-09-file-context.md`

**Interfaces:**
- Consumes: `ContextConfig`
- Produces:
  - `estimate_tokens(text: str) -> int` = `math.ceil(len(text) / 4)` (без tiktoken: ему нужна сеть для скачивания кодировок)
  - `ContextFile(BaseModel)`: `path: Path` (относительно root), `content: str`, `tokens: int`
  - `SkipReason = Literal["extension", "too_large", "not_utf8", "over_budget", "unreadable"]`; `SkippedFile`: `path: Path`, `reason: SkipReason`
  - `Context(BaseModel)`: `files: list[ContextFile] = []`, `skipped: list[SkippedFile] = []`, property `total_tokens: int`; `Context.empty()`
  - `class ContextSource(Protocol)`: `def load(self, paths: Sequence[Path]) -> Context`
  - `FileContextSource(cfg: ContextConfig, root: Path)`; пути обрабатываются в переданном порядке, бюджет `max_total_tokens` считается накопительно

- [ ] **Step 1: failing-тесты**

```python
def test_loads_allowed_files_relative_to_root(tmp_path): # a.md "hello" -> files[0].path == Path("a.md"), tokens == 2
def test_skips_disallowed_extension(tmp_path):            # x.exe -> skipped reason "extension"
def test_extension_match_is_case_insensitive(tmp_path):   # README.MD loaded
def test_skips_too_large(tmp_path):                       # max_file_kb=1, 2 KiB file -> "too_large"
def test_skips_non_utf8(tmp_path):                        # b.json bytes "привет".encode("cp1251") -> "not_utf8"
def test_skips_binary_with_nul(tmp_path):                 # b.txt b"\x00\x01" -> "not_utf8"
def test_budget_is_cumulative_and_ordered(tmp_path):      # max_total_tokens=3: a(2 tok) ok, b(2 tok) "over_budget"
def test_missing_file_is_unreadable(tmp_path):            # -> "unreadable"
```

- [ ] **Step 2:** FAIL → **Step 3:** реализация (`read_bytes`, `decode("utf-8")`, NUL-байт считается `not_utf8`, `OSError` → `unreadable`) → **Step 4:** PASS.
- [ ] **Step 5: гейт + impact + commit** `feat(context): file context source with size and token budget`.

---

### Task 4: агенты и промпты

**Files:** Create `src/ibikus/appa/agora/agents/{__init__,prompts,critic,generator}.py`, `agents/templates/{generator,critic}.md`, `tests/agents/test_prompts.py`, `tests/agents/test_agents.py`, impact `2026-11-09-agents-prompts.md`. Добавить `[tool.hatch.build] include` для `*.md` в templates, если hatch их не берёт по умолчанию (проверить `uv build` + `unzip -l`).

**Interfaces:**
- Consumes: `Context` (Task 3), `PromptsConfig` (Task 1)
- Produces:
  - `Critique(BaseModel)`: `approved: bool`, `score: int = Field(ge=0, le=10)`, `issues: list[str] = []`, `suggestions: list[str] = []`
  - `load_instructions(role: Literal["generator", "critic"], override: Path | None) -> str` — `override` или `importlib.resources` шаблон
  - `render_context(ctx: Context) -> str` — для каждого файла `"### file: {path.as_posix()}\n```\n{content}\n```"`, через пустую строку; пустой контекст → `""`
  - `build_generator_input(prompt: str, ctx: Context, previous_draft: str | None = None, critique: Critique | None = None) -> str`
  - `build_critic_input(prompt: str, ctx: Context, draft: str) -> str`
  - `build_generator(model: Model, settings: ModelSettings, instructions: str) -> Agent[None, str]`
  - `build_critic(model: Model, settings: ModelSettings, instructions: str) -> Agent[None, Critique]` — `output_type=Critique`, `retries=AgentRetries(output=2)`

Порядок секций во входе генератора: `## Context` (если не пуст) → `## Request` → при `previous_draft` секции `## Previous draft`, `## Critique` (score, issues и suggestions маркированными списками) и строка `Revise the previous draft to address every issue in the critique.` Вход критика: `## Context` → `## Request` → `## Draft`. Шаблоны: генератор — «helpful expert, answer using the context, Markdown»; критик — «strict reviewer; score 0–10; approved only if no material issues; issues must be concrete».

- [ ] **Step 1: failing-тесты**

```python
def test_render_context_headers(): assert "### file: docs/a.md" in render_context(ctx_with("docs/a.md", "x"))
def test_generator_first_iteration_has_no_revision_sections():
    s = build_generator_input("Q", Context.empty()); assert "## Request\nQ" in s and "## Previous draft" not in s and "## Context" not in s
def test_generator_revision_includes_draft_and_critique():
    s = build_generator_input("Q", Context.empty(), "D1", Critique(approved=False, score=5, issues=["too vague"]))
    assert s.index("## Previous draft") < s.index("## Critique") and "too vague" in s and "score: 5" in s
def test_critic_input_order(): s = build_critic_input("Q", ctx, "D"); assert s.index("## Context") < s.index("## Request") < s.index("## Draft")
def test_override_instructions(tmp_path): # file "custom" -> load_instructions("critic", path) == "custom"
def test_builtin_instructions_non_empty(): assert load_instructions("generator", None).strip()

async def test_critic_returns_typed_critique():
    agent = build_critic(TestModel(custom_output_args={"approved": True, "score": 9}), {}, "i")
    assert (await agent.run("x")).output == Critique(approved=True, score=9)
async def test_critic_score_out_of_range_fails_after_retries():
    # FunctionModel, всегда отдающий score=42 -> UnexpectedModelBehavior
async def test_generator_streams_text():
    # FunctionModel(stream_function=yield "he","llo") -> "".join(deltas) == "hello"
```

- [ ] **Step 2:** FAIL → **Step 3:** реализация → **Step 4:** PASS.
- [ ] **Step 5: гейт + impact + commit** `feat(agents): generator and critic agents with prompt assembly`.

---

### Task 5: reflection-граф

**Files:** Create `src/ibikus/appa/agora/reflection/{__init__,events,state,graph}.py`, `tests/reflection/test_graph.py`, `tests/reflection/fakes.py`, impact `2026-11-09-reflection-graph.md`

**Interfaces:**
- Consumes: `Critique`, `build_generator_input`, `build_critic_input` (Task 4), `Context` (Task 3), `ReflectionConfig` (Task 1)
- Produces:
  - `events.py` — pydantic-модели с полем-дискриминатором `kind: Literal[...]`:
    `IterationStarted(iteration: int, max_iterations: int)`, `DraftChunk(iteration: int, text: str)`, `DraftDone(iteration: int, text: str)`, `CritiqueDone(iteration: int, critique: Critique)`, `RunFinished(result: RunResult)`, `RunFailed(reason: Literal["cancelled", "provider_error", "critic_invalid", "invalid_input", "internal"], message: str)`;
    `RunEvent = Annotated[IterationStarted | DraftChunk | DraftDone | CritiqueDone | RunFinished | RunFailed, Field(discriminator="kind")]`;
    `IterationRecord(iteration: int, draft: str, critique: Critique)`; `RunResult(final: str, status: Literal["approved", "max_iterations"], iterations: int, best_score: int, history: list[IterationRecord])`
  - `state.py`: `ReflectionState(TypedDict)`: `prompt: str`, `context: Context`, `iteration: int`, `drafts: list[str]`, `critiques: list[Critique]`
  - `graph.py`:
    - `@dataclass(frozen=True) Agents`: `generator: Agent[None, str]`, `critic: Agent[None, Critique]`, `generator_settings: ModelSettings`, `critic_settings: ModelSettings`
    - `class CriticInvalidError(Exception)` — оборачивает `UnexpectedModelBehavior` из узла critique
    - `is_approved(c: Critique, threshold: int) -> bool` = `c.approved or c.score >= threshold`
    - `route(state: ReflectionState, cfg: ReflectionConfig) -> Literal["generate", "finalize"]`
    - `select_final(drafts: list[str], critiques: list[Critique], approved: bool) -> tuple[str, int]` → `(текст, индекс)`: при `approved` последний; иначе максимальный `score`, при равенстве — более поздний
    - `build_graph(agents: Agents, cfg: ReflectionConfig) -> CompiledStateGraph`
    - `to_result(state: ReflectionState, cfg: ReflectionConfig) -> RunResult`

Узлы: `generate` увеличивает `iteration`, пишет `IterationStarted`, затем `DraftChunk` на каждую дельту `run_stream(...).stream_text(delta=True)`, затем `DraftDone`. `critique` пишет `CritiqueDone`. События отправляются через `langgraph.config.get_stream_writer()`. Ребро после `critique` — `route`; `finalize` — пустой узел перед `END` (итог считает `to_result`).

- [ ] **Step 1: фейки** в `tests/reflection/fakes.py`: `make_agents(drafts: list[str], critiques: list[Critique | Exception]) -> Agents` на `FunctionModel`. Генератор стримит i-й draft двумя кусками, критик возвращает i-ю критику (output tool call с аргументами `Critique.model_dump()`) или бросает исключение. Плюс helper `collect(graph, prompt) -> tuple[list[RunEvent], ReflectionState]` через `astream(..., stream_mode=["custom", "values"])`.

- [ ] **Step 2: failing-тесты**

```python
async def test_approved_on_first_iteration():
    ev, st = await collect(build_graph(make_agents(["A"], [Critique(approved=True, score=9)]), cfg(max_iterations=3)), "Q")
    r = to_result(st, cfg()); assert (r.status, r.final, r.iterations) == ("approved", "A", 1)
    assert [e.kind for e in ev] == ["iteration_started", "draft_chunk", "draft_chunk", "draft_done", "critique_done"]

async def test_threshold_counts_as_approval():  # approved=False, score=8, threshold=8 -> status approved after 1
async def test_improves_until_threshold():        # scores 5, 9 -> iterations 2, final "B"
async def test_max_iterations_picks_best_draft(): # scores 6, 7, 4; max 3 -> status "max_iterations", final "B", best_score 7
async def test_tie_prefers_later_draft():         # scores 6, 6; max 2 -> final "B"
async def test_second_generation_sees_critique(): # FunctionModel фиксирует prompt 2-го вызова: содержит "## Critique" и issue-текст
async def test_critic_invalid_raises():           # critic -> UnexpectedModelBehavior -> CriticInvalidError из astream
def test_select_final_pure(): assert select_final(["a","b","c"], [c(5), c(8), c(8)], approved=False) == ("c", 2)
```

- [ ] **Step 3:** FAIL → **Step 4:** реализация → **Step 5:** PASS.
- [ ] **Step 6: гейт + impact + commit** `feat(reflection): LangGraph generate/critique loop with best-draft selection`.

---

### Task 6: ReflectionService — события, ошибки, отмена

**Files:** Create `src/ibikus/appa/agora/reflection/service.py`, `tests/reflection/test_service.py`, impact `2026-11-09-reflection-service.md`

**Interfaces:**
- Consumes: `build_graph`, `to_result`, `Agents`, `CriticInvalidError` (Task 5); `build_model`, `build_settings` (Task 2); `build_generator`, `build_critic`, `load_instructions` (Task 4); `AppConfig`
- Produces:
  - `ReflectionService(config: AppConfig, agents: Agents | None = None, observability: Observability | None = None)` — без `agents` собирает их из конфига (может бросить `ConfigError`); без `observability` используется `NoopObservability()` (Task 7). До Task 7 здесь допустим локальный no-op, Task 7 его заменит.
  - `async def run(self, prompt: str, context: Context, cancel: asyncio.Event | None = None) -> AsyncIterator[RunEvent]`
  - `config: AppConfig` (read-only property)

Поведение `run`:
- `prompt.strip() == ""` → единственное событие `RunFailed("invalid_input", "Prompt is empty")`.
- Граф выполняется во внутренней задаче и кладёт события в `asyncio.Queue`; `run` отдаёт их по мере поступления; завершается `RunFinished(to_result(...))`.
- Если `cancel` выставлен → внутренняя задача отменяется, отдаётся `RunFailed("cancelled", "Run cancelled")`, генератор завершается.
- Маппинг исключений: `ModelAPIError` → `provider_error` (message = `str(exc)`); `CriticInvalidError` → `critic_invalid`; прочее → `internal` с `logger.exception`. После `RunFailed` событий больше нет.

- [ ] **Step 1: failing-тесты**

```python
async def test_happy_path_ends_with_run_finished(): # last event RunFinished, result.status == "approved"
async def test_empty_prompt(): assert [e async for e in svc.run("   ", Context.empty())] == [RunFailed(reason="invalid_input", message="Prompt is empty")]
async def test_provider_error_becomes_run_failed():
    # generator FunctionModel raises ModelConnectionError("m", "connection refused")  # subclass of ModelAPIError
    assert last.reason == "provider_error" and "connection refused" in last.message
async def test_critic_invalid_becomes_run_failed():  # reason "critic_invalid"
async def test_cancel_after_first_chunk():
    # генератор с медленным стримом (asyncio.sleep(10) между кусками); выставить cancel после первого DraftChunk
    assert events[-1].reason == "cancelled"  # в пределах 1 с (asyncio.timeout(1))
async def test_unexpected_exception_is_internal(): # generator raises RuntimeError("boom") -> reason "internal"
```

- [ ] **Step 2:** FAIL → **Step 3:** реализация → **Step 4:** PASS.
- [ ] **Step 5: гейт + impact + commit** `feat(reflection): service facade with error mapping and cancellation`.

---

### Task 7: observability (Langfuse)

**Files:** Create `src/ibikus/appa/agora/observability/{__init__,langfuse}.py`, `tests/observability/test_langfuse.py`; Modify `reflection/graph.py`, `reflection/service.py`; impact `2026-11-09-langfuse-tracing.md`

**Interfaces:**
- Consumes: `LangfuseConfig` (Task 1), `ReflectionService` (Task 6)
- Produces:
  - `class Observability(Protocol)`: `state: Literal["off", "on", "error"]`; `def run_span(self, prompt: str, metadata: dict[str, Any]) -> AbstractContextManager[SpanHandle]`; `def iteration_span(self, iteration: int) -> AbstractContextManager[SpanHandle]`; `def flush(self) -> None`
  - `class SpanHandle(Protocol)`: `def update(self, *, output: Any = None, metadata: dict[str, Any] | None = None) -> None`
  - `NoopObservability()` — `state="off"`
  - `LangfuseObservability(client: langfuse.Langfuse)` — `run_span` = `client.start_as_current_observation(name="reflection-run", as_type="agent", input=prompt, metadata=...)`, `iteration_span` = `as_type="chain", name=f"iteration-{n}"`
  - `setup_observability(cfg: LangfuseConfig, env: Mapping[str, str] | None = None) -> Observability`: `off` → Noop; `auto` без обоих ключей → Noop (`state="off"`); `on` без ключей → Noop с `state="error"` и warning в лог; при ключах — `Langfuse()` + `Agent.instrument_all()`; любое исключение инициализации → warning + Noop(`state="error"`)

Интеграция: сигнатура меняется на `build_graph(agents: Agents, cfg: ReflectionConfig, observability: Observability) -> CompiledStateGraph`, и Task 5-тесты передают `NoopObservability()`. Сервис оборачивает прогон в `run_span(prompt, {"generator": describe(gen), "critic": describe(critic)})`, узел `generate` открывает `iteration_span(n)`, узел `critique` вызывает `update(metadata={"score": c.score, "approved": c.approved})` на span итерации. По завершении — `run_span.update(output=result.final, metadata={"status": ..., "iterations": ...})`. Generations создаёт сама инструментация Pydantic AI (модель и параметры попадают в OTel-атрибуты).

- [ ] **Step 1: failing-тесты**

```python
def test_off(): assert setup_observability(LangfuseConfig(enabled="off"), env={}).state == "off"
def test_auto_without_keys_is_off(): assert setup_observability(LangfuseConfig(), env={}).state == "off"
def test_on_without_keys_is_error(): assert setup_observability(LangfuseConfig(enabled="on"), env={}).state == "error"
def test_init_failure_degrades(monkeypatch):  # monkeypatch Langfuse ctor to raise -> state "error", no exception
async def test_service_records_spans():
    # FakeObservability, записывающий вызовы; один прогон с 2 итерациями ->
    assert rec.calls == ["run", "iter-1", "update-iter-1", "iter-2", "update-iter-2", "update-run"]
```

- [ ] **Step 2:** FAIL → **Step 3:** реализация → **Step 4:** PASS (включая все тесты Task 5–6).
- [ ] **Step 5: гейт + impact + commit** `feat(observability): optional Langfuse tracing of reflection runs`.

---

### Task 8: TUI — главный экран

**Files:** Create `src/ibikus/appa/agora/tui/{__init__,app,files_panel,run_feed,status_bar}.py`, `tui/agora.tcss`, `tests/tui/test_app.py`, `tests/tui/test_snapshots.py`; impact `2026-11-09-tui-main-screen.md`

**Interfaces:**
- Consumes: `ReflectionService.run` (Task 6), `FileContextSource` (Task 3), `RunEvent` (Task 5), `describe` (Task 2), `Observability.state` (Task 7)
- Produces:
  - `AgoraApp(config: AppConfig, root: Path, service_factory: Callable[[AppConfig], ReflectionService], observability_state: str = "off")`; атрибуты: `last_result: RunResult | None`, `last_prompt: str`, `is_running: bool`; методы `action_run()`, `action_cancel()`, `rebuild_service(config: AppConfig) -> None` (используется в Task 9)
  - `FilesPanel(DirectoryTree)`: `marked: set[Path]` (абсолютные пути); биндинги `space` и `insert` переключают отметку файла под курсором (каталоги игнорируются); помеченные узлы рисуются с префиксом `[x] `, остальные файлы — `[ ] `; сообщение `FilesPanel.MarkedChanged(marked: frozenset[Path])`
  - `RunFeed(VerticalScroll)`: `clear()`, `apply(event: RunEvent) -> None`. На каждую итерацию — `Collapsible(title=f"Iter {n}")` с `Static` черновика (дополняется по `DraftChunk`) и `Static` критики (`score {s}/10` + issues). Предыдущие итерации сворачиваются при старте новой. `RunFinished` → блок `Final ({status}, score {best})` с CSS-классом `final`. `RunFailed` → блок с классом `error` и текстом `"{reason}: {message}"`
  - `StatusBar(Static)`: `set_models(gen: str, critic: str)`, `set_langfuse(state: str)` → `Gen: … │ Critic: … │ Langfuse ●/○/✕`
  - Заголовок ленты: `Run ─ iter {i}/{max} ─ score {prev} → {cur}`

Раскладка (spec §5): слева `FilesPanel` (ширина 32, рамка `Files`, подпись снизу `Context: {n} files, {tokens/1000:.1f}k`), справа `TextArea` (`id="prompt"`, рамка `Prompt`, высота 8) и над ней `RunFeed` (рамка `Run`); ниже `StatusBar`, затем `Footer`. Биндинги в этом задании: `f2` и `ctrl+enter` → `run`, `escape` → `cancel`, `f10` → `quit`. Остальные F-клавиши объявляются в Task 9. Тема `.tcss`: фон `#000080`, текст `#c0c0c0`, рамки `#00ffff`, выделение курсора `#008080`, `final` `#ffff00`, `error` `#ff5555`.

`action_run`: при `is_running` → `notify("A run is already in progress")`; пустой промпт → `notify("Prompt is empty", severity="warning")`; иначе `FileContextSource.load(sorted(marked))` → `RunFeed.clear()` → `@work(exclusive=True)` перебирает `service.run(prompt, ctx, cancel_event)` и вызывает `RunFeed.apply` для каждого события. `context.skipped` не пуст → `notify` с перечнем причин. `action_cancel` выставляет `cancel_event`. На `MarkedChanged` пересчитывается подпись контекста.

- [ ] **Step 1: failing-тесты** (через `app.run_test()` и `Pilot`; `service_factory` отдаёт сервис на фейковых `Agents` из `tests/reflection/fakes.py`; `root` = `tmp_path` с файлами `a.md`, `b.txt`):

```python
async def test_mark_file_updates_context_label():   # фокус на дереве, курсор на a.md, press("space") -> "Context: 1 files" в подписи
async def test_run_shows_iterations_and_final():    # ввести "Q", press("f2"), дождаться app.workers -> RunFeed содержит "Iter 1", "Final (approved"
async def test_empty_prompt_notifies():             # press("f2") без текста -> notification "Prompt is empty", RunFeed пуст
async def test_second_run_while_running_is_rejected(): # медленный фейк; f2, f2 -> notification "A run is already in progress"
async def test_escape_cancels():                    # медленный фейк; f2, escape -> блок error с "cancelled"
async def test_provider_error_shown_not_crash():    # фейк бросает ModelAPIError -> блок error с "provider_error", app всё ещё running
```

`tests/tui/test_snapshots.py`: `snap_compare(app, terminal_size=(100, 30))` для начального экрана и экрана после одобренного прогона (эталоны генерируются `--snapshot-update` и коммитятся).

- [ ] **Step 2:** FAIL → **Step 3:** реализация → **Step 4:** PASS; snapshot создать через `uv run pytest tests/tui --snapshot-update`, открыть HTML-отчёт и визуально сверить со spec §5.
- [ ] **Step 5: гейт + impact + commit** `feat(tui): Far-style main screen with files, prompt and live run feed`.

---

### Task 9: TUI — диалоги и действия (F1, F3, F4, F5, F6, F9)

**Files:** Create `src/ibikus/appa/agora/tui/dialogs.py`, `src/ibikus/appa/agora/reflection/export.py`, `tests/tui/test_dialogs.py`, `tests/reflection/test_export.py`; Modify `tui/app.py`; impact `2026-11-09-tui-dialogs.md`

**Interfaces:**
- Consumes: `AgoraApp.last_result`, `last_prompt`, `rebuild_service` (Task 8); `RunResult` (Task 5); `AppConfig`, `ModelConfig` (Task 1)
- Produces:
  - `render_run_markdown(prompt: str, result: RunResult, created: datetime) -> str` — `# Agora run {created:%Y-%m-%d %H:%M}`, `## Prompt`, `## Final answer ({status}, score {best_score})`, `## Iterations` с `### Iteration n — score s` + draft + issues
  - `HelpScreen(ModalScreen)` — таблица клавиш; `ViewerScreen(ModalScreen)` — `MarkdownViewer(result.final)`; `ConfigScreen(ModalScreen)` — `config.model_dump_json(indent=2)` в read-only `TextArea`; `ModelsScreen(ModalScreen[AppConfig | None])` — для generator и critic: `Select` провайдера, `Input` имени, `Input` температуры; кнопки `Apply` / `Cancel`; невалидная температура → `Label` с ошибкой pydantic, экран не закрывается
- Биндинги: `f1` help, `f3` view, `f4` config, `f5` copy (`app.copy_to_clipboard(last_result.final)` + `notify("Copied")`), `f6` save (`{root}/agora-runs/{ts:%Y%m%d-%H%M%S}.md`, `notify(f"Saved to {path}")`), `f9` models (результат → `rebuild_service(new_cfg)` + обновить `StatusBar`; YAML не трогается). Если `last_result is None`: F3/F5/F6 → `notify("Nothing to copy/save yet")`, файл не создаётся.

- [ ] **Step 1: failing-тесты**

```python
def test_render_run_markdown(): # содержит "## Prompt\nQ", "## Final answer (approved, score 9)", "### Iteration 1 — score 9"
async def test_f6_saves_markdown(tmp_path):     # после прогона f6 -> ровно один файл в tmp_path/"agora-runs", содержит "## Final answer"
async def test_f5_f6_without_result(tmp_path):  # f5 -> "Nothing to copy/save yet"; f6 -> то же, папки agora-runs нет
async def test_f9_changes_generator_temperature():
    # f9, temperature generator = "0.5", Apply -> app.config.reflection.generator.temperature == 0.5,
    # service_factory вызвана повторно, StatusBar содержит "t=0.5", config/agora.yaml не изменился (mtime)
async def test_f9_invalid_temperature_keeps_dialog(): # "5" -> экран ModelsScreen всё ещё активен, текст ошибки виден
async def test_f1_f3_f4_open_screens():         # соответствующий screen на вершине стека; escape закрывает
```

- [ ] **Step 2:** FAIL → **Step 3:** реализация → **Step 4:** PASS (+ snapshot для `HelpScreen`).
- [ ] **Step 5: гейт + impact + commit** `feat(tui): help, viewer, config, copy, save and model-switch dialogs`.

---

### Task 10: CLI-вход и логирование

**Files:** Create `src/ibikus/appa/agora/__main__.py`, `src/ibikus/appa/agora/logging_setup.py`, `tests/test_main.py`; impact `2026-11-09-cli-entry.md`

**Interfaces:**
- Consumes: `load_config`, `ConfigError`, `setup_observability`, `ReflectionService`, `AgoraApp`
- Produces:
  - `setup_logging(home: Path) -> Path` — `RotatingFileHandler(home/"logs"/"agora.log", maxBytes=1_000_000, backupCount=3)` на root logger, уровень из `AGORA_LOG_LEVEL` (дефолт `INFO`), без stream handler; возвращает путь к файлу
  - `main(argv: list[str] | None = None) -> int` — argparse: `--config PATH`, `--root PATH` (дефолт cwd), `--version`. Шаги: `load_dotenv()` → `setup_logging(Path(os.environ.get("AGORA_HOME", "~/.agora")).expanduser())` → `load_config` (при `ConfigError` печатает в stderr `"Invalid configuration:\n{e}"` и возвращает `2`) → пробная сборка сервиса (`ConfigError` из фабрики, например нет ключа, тоже даёт `2`) → `setup_observability` → `AgoraApp(...).run()` → `observability.flush()` → `0`
  - `if __name__ == "__main__": sys.exit(main())`

- [ ] **Step 1: failing-тесты**

```python
def test_invalid_config_exit_2(tmp_path, capsys):  # yaml approve_threshold: 11 -> main(["--config", p]) == 2, stderr содержит "reflection.approve_threshold"
def test_missing_api_key_exit_2(tmp_path, capsys, monkeypatch):  # critic anthropic, ключа нет -> 2, "ANTHROPIC_API_KEY is not set"
def test_version(capsys):  # main(["--version"]) печатает "agora 0.1.0" (SystemExit 0)
def test_logging_goes_to_file(tmp_path):  # setup_logging(tmp_path); logging.getLogger("x").info("hi") -> файл содержит "hi"
def test_banner_env_set(): import ibikus.appa.agora; assert os.environ["PYDANTIC_AI_NO_BANNER"] == "1"
```

`AgoraApp.run` в тестах не вызывается: monkeypatch `AgoraApp.run` → `lambda self: None`, плюс тест `test_happy_path_returns_0`.

- [ ] **Step 2:** FAIL → **Step 3:** реализация → **Step 4:** PASS.
- [ ] **Step 5: ручная проверка:** `uv run agora --version`; `uv run agora` в Windows Terminal (WSL2) — экран соответствует spec §5, F10 выходит, баннера нет.
- [ ] **Step 6: гейт + impact + commit** `feat(cli): agora entry point with config validation and file logging`.

---

### Task 11: Langfuse compose, CI, документация

**Files:** Create `docker/langfuse/compose.yaml`, `docker/langfuse/README.md`, `.github/workflows/ci.yml`, `docs/architecture.md`, `docs/configuration.md`, `docs/troubleshooting.md`; Modify `docs/start.md`; impact `2026-11-09-infra-docs.md`

- [ ] **Step 1: compose.** Взять официальный `docker-compose.yml` из репозитория `langfuse/langfuse` (ветка `main`, self-hosting v3: web, worker, postgres, clickhouse, redis, minio), сохранить как `docker/langfuse/compose.yaml`, закрепить теги образов `langfuse/langfuse` и `langfuse/langfuse-worker` на конкретной мажорной версии (не `latest`), сменить секреты на `${VAR:-changeme}`. В `README.md` описать `docker compose -f docker/langfuse/compose.yaml up -d`, UI на `http://localhost:3000`, где взять ключи и что вписать в `.env` (`LANGFUSE_HOST=http://localhost:3000`).
  Проверка: `docker compose -f docker/langfuse/compose.yaml config -q` → exit 0.
- [ ] **Step 2: CI** `.github/workflows/ci.yml`: на `push` и `pull_request`, `ubuntu-latest`, `astral-sh/setup-uv@v6`, `uv sync --frozen`, затем `ruff check`, `ruff format --check`, `mypy src`, `pytest`. Перед этим закоммитить `uv.lock`.
- [ ] **Step 3: документация** (англ., docs-as-code): `architecture.md` — слои, схема графа, поток событий, точки расширения для циклов 2–5; `configuration.md` — все поля `AppConfig` с дефолтами, приоритет источников, env-переопределения с примерами, секреты; `troubleshooting.md` — Ollama не отвечает, нет ключа (exit 2), баннер или мусор в терминале, Langfuse ✕, где лог; `start.md` — добавить Langfuse и `uv run pytest -m integration`.
- [ ] **Step 4: integration-тест** `tests/integration/test_ollama.py` (`@pytest.mark.integration`): прогон с `ollama/qwen2.5:7b` на обеих ролях даёт `RunFinished`. Запуск: `uv run pytest -m integration`, при недоступном Ollama — skip через проверку `GET http://localhost:11434/api/tags`.
- [ ] **Step 5: гейт + impact + commit** `chore: Langfuse self-hosting, CI pipeline and project docs`.

---

### Task 12: финальная проверка

- [ ] **Step 1:** `uv sync --frozen && uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest` — всё зелёное, без warnings про незакрытые задачи.
- [ ] **Step 2: сверка со spec:** пройти разделы 2–9 spec и для каждого требования назвать тест или ручную проверку; найденные пробелы закрыть отдельным коммитом с impact.
- [ ] **Step 3: ручной smoke** в Windows Terminal: отметить 2 файла, промпт, F2 → стриминг, итерации, Final; Esc во время прогона; F6 → файл в `agora-runs/`; F9 → сменить температуру. При поднятом Langfuse — trace `reflection-run` с итерациями и generations.
- [ ] **Step 4:** обновить статус spec на «реализовано (MVP)», commit `docs: mark MVP spec as implemented`.
