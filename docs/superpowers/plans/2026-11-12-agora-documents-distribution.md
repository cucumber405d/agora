# Agora: документы и распространяемый продукт — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить документы (PDF/DOCX/PPTX/XLSX/HTML) в контекст и превратить Agora в распространяемый Windows-продукт. В продукт входят:
- мастер первого запуска с диагностикой системы, установкой Ollama и скачиванием моделей;
- Setup.exe;
- релизы на GitHub.

**Architecture:**
- Конвертация документов вынесена в `context/documents.py` (markitdown + кеш + таймаут) и подключена к существующему `FileContextSource`.
- Пакет `setup/` не зависит от Textual. Его используют TUI-мастер (`tui/setup_wizard.py`) и CLI (`agora doctor`, `agora setup`).
- Внешний мир (HTTP, процессы, реестр) внедряется через параметры, поэтому всё тестируется без сети и без Windows.
- Сборка: PyInstaller onedir + Inno Setup в `release.yml` по тегу.

**Tech Stack:**
- новые зависимости: markitdown[pdf,docx,pptx,xlsx] 0.1.x, psutil;
- dev-зависимость: pyinstaller;
- существующие: httpx, Textual 8.2;
- сборка: Inno Setup 6, GitHub Actions `windows-latest`.

**Spec:** `docs/superpowers/specs/2026-11-12-agora-documents-distribution-design.md`

## Global Constraints

- Интерфейс, комментарии в коде, README и `user-guide.md` — на английском. Спеки и планы — на русском.
- Каждая задача добавляет импакт `docs/impacts/2026-11-12-<slug>.md` с разделами `## RU` и `## EN` (What changed / Why / Impact).
- Python ≥ 3.12; ruff, ruff format, mypy strict, pytest должны быть зелёными перед каждым коммитом. Коды возврата проверяются явно, без пайпов.
- Не коммитить `config/agora.yaml` и `Claude outputs/`.
- Модули `setup/*` не импортируют Textual.
- Права администратора не требуются: Inno Setup `PrivilegesRequired=lowest`, переменные Ollama пишутся в `HKCU\Environment`.
- Таймауты:
  - конвертация документа — 60 с (`convert_timeout_s`);
  - ожидание сервера Ollama — 120 с;
  - внешние команды — 10 с.
- `max_document_mb` по умолчанию — 20.
- URL установщика: `https://ollama.com/download/OllamaSetup.exe`.
- Пользовательские данные — в `~/.agora/` (или `AGORA_HOME`): `config.yaml`, `config.yaml.bak`, `logs/`, `downloads/`.
- Первый релиз — `0.2.0`. Тег `v*` обязан совпадать с `__version__`.

## Review Focus

1. **Путь с кириллицей или пробелами** (`C:\Users\Дмитрий\Мои документы\отчёт.pdf`) — конвертация и превью работают. Тест в Task 2.
2. **Файл изменился между отметкой и запуском** — кеш не отдаёт старый текст. Ключ включает `mtime_ns` и `size`. Тест в Task 2.
3. **Ollama запущена, но `/api/pull` вернул `{"error": ...}`** (например, нет такой модели) — ошибка показывается, а не «успех». Тест в Task 7.
4. **Повторный запуск мастера при существующем конфиге** — старый сохранён в `.bak`, пользовательские поля, которых нет в конфигурации (`observability`, `prompts`), не потеряны. Тест в Task 6.
5. **`nvidia-smi` есть, но выдаёт ошибку или несколько GPU** — берётся GPU с максимальной VRAM, ошибка даёт ⚠, а не падение. Тест в Task 4.

---

### Task 1: Пути пользователя и порядок поиска конфига

**Files:**
- Create: `src/ibikus/appa/agora/paths.py`
- Modify: `src/ibikus/appa/agora/config/loader.py`, `src/ibikus/appa/agora/__main__.py`
- Test: `tests/test_paths.py`, `tests/config/test_loader.py`
- Docs: `docs/configuration.md` (порядок поиска), импакт `config-search-order`

**Interfaces:**
- Produces:
  - `agora_home(env: Mapping[str, str] | None = None) -> Path` — `AGORA_HOME` или `~/.agora`, с `expanduser`;
  - `user_config_path(env=None) -> Path` — `agora_home()/"config.yaml"`;
  - `downloads_dir(env=None) -> Path`;
  - `is_frozen() -> bool` — `getattr(sys, "frozen", False)`;
  - `find_config_path(path: Path | None, env: Mapping[str, str], cwd: Path) -> Path | None` в `loader.py`;
  - `load_config(path=None, env=None, cwd=None)` — сигнатура прежняя.

- [ ] **Step 1: Тесты**
  - `test_agora_home_respects_env`: `agora_home({"AGORA_HOME": str(tmp)}) == tmp`.
  - `test_agora_home_default`: результат оканчивается на `.agora`.
  - `test_find_config_prefers_cwd_over_home`: есть и `cwd/config/agora.yaml`, и `home/config.yaml` → возвращается cwd-вариант.
  - `test_find_config_falls_back_to_home`: есть только `AGORA_HOME/config.yaml` → возвращается он.
  - `test_find_config_none_when_nothing`: возвращает `None`.
  - Существующие тесты на `--config` и `AGORA_CONFIG` остаются зелёными.
- [ ] **Step 2: Запустить** `uv run pytest tests/test_paths.py tests/config -v` — FAIL (нет модуля).
- [ ] **Step 3: Реализовать.**
  - `paths.py`.
  - `_resolve_path` переименовать в публичную `find_config_path`, добавить последний шаг `user_config_path(env)`.
  - В `__main__.py` заменить `Path(os.environ.get("AGORA_HOME", ...))` на `agora_home()`.
- [ ] **Step 4: Запустить** полный набор: `uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest` — PASS.
- [ ] **Step 5: Коммит** `feat(config): look up ~/.agora/config.yaml as the last config source`.

### Task 2: Конвертация документов

**Files:**
- Create: `src/ibikus/appa/agora/context/documents.py`, `scripts/make_doc_fixtures.py`, `tests/fixtures/docs/` (`sample.pdf`, `sample.docx`, `sample.pptx`, `sample.xlsx`, `sample.html`, `scan.pdf` — без текстового слоя, `broken.pdf`, `old.doc`)
- Modify:
  - `context/models.py` — `SkipReason` + поле `source_format`;
  - `context/files.py`;
  - `config/models.py` — `ContextConfig`;
  - `pyproject.toml` — markitdown, psutil;
  - `agents/prompts.py` — заголовок файла.
- Test: `tests/context/test_documents.py`, `tests/context/test_files.py`, `tests/agents/test_prompts.py`
- Docs: `docs/configuration.md`, импакт `documents-in-context`

**Interfaces:**
- Produces:
  - `DOCUMENT_FORMATS: dict[str, str]` = `{".pdf": "PDF", ".docx": "DOCX", ".pptx": "PPTX", ".xlsx": "XLSX", ".html": "HTML", ".htm": "HTML"}`;
  - `LEGACY_EXT = {".doc", ".xls", ".ppt"}`;
  - `class ConversionError(Exception)`;
  - `class DocumentConverter`:
    - `__init__(self, timeout_s: float = 60, convert: Callable[[Path], str] | None = None)` — `convert` по умолчанию вызывает `MarkItDown().convert(str(path)).text_content`;
    - `def to_markdown(self, path: Path) -> str` — бросает `ConversionError`, а при таймауте `ConversionError("timeout")`;
    - кеш `dict[tuple[str, int, int], str]` по `(str(resolved), st_mtime_ns, st_size)`;
  - `SkipReason` дополнен `"legacy_format" | "no_text" | "convert_failed"`;
  - `ContextFile.source_format: str | None = None` («PDF» и т. п.);
  - `ContextConfig`: `max_document_mb: int = Field(20, ge=1)`, `convert_timeout_s: float = Field(60, gt=0)`; к `allowed_ext` по умолчанию добавлены ключи `DOCUMENT_FORMATS`;
  - `FileContextSource.__init__(self, cfg, root, converter: DocumentConverter | None = None)`;
  - `FileContextSource.load(self, paths, on_progress: Callable[[int, int], None] | None = None) -> Context` — `on_progress(done, total)` вызывается после каждого документа.

- [ ] **Step 1: Фикстуры.**
  - `scripts/make_doc_fixtures.py` генерирует их через `python-docx`, `python-pptx`, `openpyxl` (приходят с markitdown) и `reportlab` (dev-зависимость):
    - `sample.pdf` с текстом «Agora sample PDF», остальные форматы — с аналогичным текстом;
    - `scan.pdf` — только картинка;
    - `broken.pdf` — первые 200 байт `sample.pdf`;
    - `old.doc` — любые байты.
  - Запустить скрипт и закоммитить бинарники.
- [ ] **Step 2: Тесты `test_documents.py`:**
  - `test_converts_each_format` (параметризован по 5 форматам): результат содержит `"Agora sample"`;
  - `test_cache_hit_skips_second_convert`: счётчик вызовов фейкового `convert` == 1 после двух вызовов;
  - `test_cache_invalidated_on_change`: перезапись файла (другой размер) → 2 вызова (Review Focus 2);
  - `test_timeout_raises`: фейковый `convert` спит 1 с, `timeout_s=0.1` → `ConversionError`;
  - `test_broken_pdf_raises_conversion_error`;
  - `test_unicode_path` — копия `sample.pdf` в `tmp/Мои документы/отчёт.pdf` конвертируется (Review Focus 1).
- [ ] **Step 3: Тесты `test_files.py`:**
  - `test_document_loaded_with_format`: `files[0].source_format == "PDF"`;
  - `test_legacy_format_skipped` → `"legacy_format"`;
  - `test_scan_pdf_no_text` → `"no_text"` (пустой или пробельный результат);
  - `test_broken_pdf_convert_failed` → `"convert_failed"`;
  - `test_document_size_limit_uses_mb`: `max_document_mb=1`, файл 2 МБ → `"too_large"`, при этом `max_file_kb` на документы не влияет;
  - `test_document_counts_toward_budget` → `"over_budget"`;
  - `test_on_progress_called`: `[(1, 2), (2, 2)]` для двух документов.
- [ ] **Step 4: Тест `test_prompts.py`:** `render_context` для `ContextFile(source_format="PDF")` выдаёт строку `### file: x.pdf (converted from PDF)`, для обычного файла заголовок прежний.
- [ ] **Step 5: Запустить** — FAIL.
- [ ] **Step 6: Реализовать.**
  - Таймаут: `concurrent.futures.ThreadPoolExecutor(max_workers=1)` + `future.result(timeout)`. Зависший поток не ждать: `shutdown(wait=False)`.
  - В `_read` проверки идут в таком порядке:
    1. `LEGACY_EXT`;
    2. неразрешённое расширение;
    3. документ: размер по `max_document_mb`, затем конвертация;
    4. обычный файл: прежняя логика.
  - Исключения markitdown → `convert_failed` с `logger.warning(..., exc_info=True)`.
- [ ] **Step 7: Запустить** полный набор — PASS.
- [ ] **Step 8: Коммит** `feat(context): convert PDF/DOCX/PPTX/XLSX/HTML via markitdown`.

### Task 3: Документы в TUI — фоновая загрузка, прогресс и превью

**Files:**
- Modify:
  - `tui/app.py` — `on_files_panel_marked_changed`, `action_run`;
  - `tui/files_panel.py` — Enter на файле;
  - `tui/progress.py` — этап контекста;
  - `tui/dialogs.py` — `ViewerScreen(title)`.
- Test: `tests/tui/test_app.py`, `tests/tui/test_files_panel.py`, `tests/tui/test_snapshots.py`
- Docs: импакт `documents-tui`

**Interfaces:**
- Consumes: `FileContextSource.load(paths, on_progress)`, `DocumentConverter`.
- Produces:
  - один `DocumentConverter` на всё время жизни `AgoraApp` (атрибут `self._converter`), чтобы кеш переживал перезагрузку контекста;
  - `FilesPanel.FileOpened(Message)` с полем `path: Path`;
  - `ViewerScreen(markdown: str, title: str = "Result")`;
  - `ProgressPanel.context_progress(done: int, total: int) -> None` — строка `Context: converting {done}/{total}`.

- [ ] **Step 1: Тесты.**
  - `test_marking_document_counts_tokens`: отметить `sample.pdf` → подпись `Context: 1 files, …` появляется после завершения группы воркеров `"context"` (`wait_group(app, "context")`).
  - `test_run_waits_for_conversion`: фейковый converter с задержкой; F2 сразу после отметки → в промпт генератора (fake service) попал текст документа.
  - `test_enter_on_document_opens_preview`: Enter на `sample.pdf` → `ViewerScreen`, заголовок содержит `sample.pdf` и `tokens`.
  - `test_enter_on_legacy_doc_shows_reason`: в тексте превью есть `legacy_format`.
  - Snapshot `test_snapshot_document_preview`.
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать.**
  - Загрузку контекста перенести в `@work(group="context", exclusive=True)` с `asyncio.to_thread(source.load, paths, on_progress)`; `on_progress` → `call_from_thread(progress.context_progress, …)`.
  - `action_run` при запущенной загрузке ждёт её результата (обычный `await` внутри воркера `_run`) и только потом стартует сервис.
  - `FilesPanel`: в `on_directory_tree_file_selected` отправлять `FileOpened`; приложение строит превью через `source.load([path])`.
- [ ] **Step 4: Запустить** полный набор, включая snapshot (`--snapshot-update` только для нового снапшота, старые должны совпасть) — PASS.
- [ ] **Step 5: Коммит** `feat(tui): background document conversion, progress and preview`.

### Task 4: Диагностика системы

**Files:**
- Create:
  - `src/ibikus/appa/agora/setup/__init__.py`;
  - `setup/diagnostics.py`;
  - `setup/runner.py`;
  - образцы в `tests/setup/samples/`: `nvidia_smi_one.txt`, `nvidia_smi_two.txt`, `ollama_ps.txt`.
- Test: `tests/setup/test_diagnostics.py`
- Docs: импакт `diagnostics`

**Interfaces:**
- Produces:
  - `runner.py`:
    - `Runner = Callable[[Sequence[str], float], CommandResult]`;
    - `@dataclass(frozen=True) CommandResult(returncode: int, stdout: str, stderr: str)`;
    - `run_command(args, timeout_s=10) -> CommandResult` — `FileNotFoundError` → `returncode=127`, таймаут → `returncode=124`;
  - `diagnostics.py`:
    - `Status = Literal["ok", "warn", "error"]`;
    - `@dataclass(frozen=True) Check(name: str, status: Status, detail: str)`;
    - `@dataclass(frozen=True) Gpu(name: str, vram_gb: float | None)`;
    - `@dataclass(frozen=True) OllamaInfo(installed: bool, running: bool, version: str | None, models: tuple[str, ...], env: dict[str, str])`;
    - `@dataclass(frozen=True) SystemReport(os: str, ram_gb: float, free_disk_gb: float, gpu: Gpu | None, ollama: OllamaInfo, checks: tuple[Check, ...])`, свойство `worst: Status`;
    - `parse_nvidia_smi(text: str) -> Gpu | None` — GPU с максимальной VRAM, МиБ → ГБ (/1024);
    - `parse_ollama_ps(text: str) -> list[LoadedModel]`, где `LoadedModel(name: str, processor: str, context: int | None)`;
    - `ollama_models_dir(env) -> Path` — `OLLAMA_MODELS` или `~/.ollama/models`;
    - `find_ollama_exe(env, which=shutil.which) -> Path | None` — PATH, затем `%LOCALAPPDATA%/Programs/Ollama/ollama.exe`;
    - `async collect(*, base_url: str = "http://localhost:11434", runner: Runner = run_command, client: httpx.AsyncClient | None = None, env: Mapping[str, str] | None = None, network: bool = True) -> SystemReport`.

- [ ] **Step 1: Тесты.**
  - `test_parse_nvidia_one`: `"NVIDIA GeForce RTX 4070, 12282"` → `Gpu("NVIDIA GeForce RTX 4070", ≈12.0)`.
  - `test_parse_nvidia_picks_largest`: два GPU → берётся тот, у которого больше VRAM (Review Focus 5).
  - `test_parse_nvidia_garbage_returns_none`.
  - `test_parse_ollama_ps`: строка с `qwen3:14b … 100% GPU … 8192` → `LoadedModel("qwen3:14b", "100% GPU", 8192)`.
  - `test_collect_no_nvidia_smi`: runner возвращает 127, а на Windows-ветке PowerShell отдаёт `"Intel UHD"` → `gpu == Gpu("Intel UHD", None)`, check `GPU` со статусом `warn`.
  - `test_collect_nvidia_smi_error`: returncode 9 → `warn`, без исключения (Review Focus 5).
  - `test_collect_ollama_running`: `httpx.MockTransport` — `/api/version` → `{"version":"0.12.3"}`, `/api/tags` → две модели.
  - `test_collect_ollama_down`: `ConnectError` → `running=False`, check `Ollama` со статусом `error`.
  - `test_collect_network_false_skips_http`: транспорт, падающий при любом запросе, не вызывается.
  - `test_check_isolation`: если `psutil.virtual_memory` бросает исключение (monkeypatch), остальные проверки на месте, RAM — `warn`.
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать.**
  - Не-NVIDIA GPU на Windows: `powershell -NoProfile -Command "(Get-CimInstance Win32_VideoController).Name"`, берётся первая непустая строка.
  - Ollama env читается из `env` (по умолчанию `os.environ`) по трём ключам.
  - Каждая проверка обёрнута в `try/except Exception` → `Check(..., "warn", str(e))`.
- [ ] **Step 4: Запустить** полный набор — PASS.
- [ ] **Step 5: Коммит** `feat(setup): system diagnostics report`.

### Task 5: Конфигурации и выбор рекомендуемой

**Files:**
- Create: `setup/presets.py`, `setup/presets.yaml`
- Test: `tests/setup/test_presets.py`
- Docs: `docs/configuration.md` (раздел Presets), импакт `presets`

**Interfaces:**
- Consumes: `SystemReport`, `Gpu`.
- Produces:
  - `class Preset(BaseModel)`: `id: str`, `title: str`, `generator: str`, `critic: str`, `download_gb: float`, `min_ram_gb: float | None = None`, `min_vram_gb: float | None = None`, `ollama_context: int`, `max_total_tokens: int`;
  - `load_presets() -> list[Preset]` — через `importlib.resources`, порядок от слабой к сильной;
  - `unmet(preset: Preset, report: SystemReport) -> list[str]` — человекочитаемые причины, например `"needs 12 GB VRAM (found 8.0)"` или `"GPU memory unknown"`;
  - `recommend(presets: Sequence[Preset], report: SystemReport) -> Preset | None` — самая сильная без `unmet`. Если VRAM неизвестна, учитываются только пресеты без `min_vram_gb`; если подходящих нет — `None`;
  - `default_choice(presets, report) -> Preset` — `recommend(...)` или первый пресет (`light`);
  - `disk_shortfall_gb(preset, report) -> float` — `max(0, download_gb + 2 - free_disk_gb)`.

`presets.yaml` — значения из спеки §4.3:

```yaml
- {id: light, title: Light, generator: "qwen3:4b", critic: "qwen3:4b", download_gb: 2.5, min_ram_gb: 8, ollama_context: 4096, max_total_tokens: 2500}
- {id: standard, title: Standard, generator: "qwen3.5:9b", critic: "qwen3:8b", download_gb: 11, min_vram_gb: 8, ollama_context: 8192, max_total_tokens: 4500}
- {id: quality, title: Quality, generator: "qwen3.5:9b", critic: "qwen3:14b", download_gb: 15, min_vram_gb: 12, ollama_context: 8192, max_total_tokens: 4500}
```

- [ ] **Step 1: Тесты** (параметризованная таблица `(ram, gpu, ожидаемый recommend)`):
  - `(16, None) → light`;
  - `(16, Gpu("RTX 3060 Ti", 8)) → standard`;
  - `(32, Gpu("RTX 4070", 12)) → quality`;
  - `(32, Gpu("Intel UHD", None)) → light`, `unmet(standard)` содержит `"GPU memory unknown"`;
  - `(4, None) → None`, `default_choice → light`.

  Плюс `test_disk_shortfall`: `free_disk_gb=10`, `quality` → `7.0`.
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать.** Добавить `presets.yaml` в package data (hatch включает его по умолчанию; проверить, что `load_presets()` работает из wheel).
- [ ] **Step 4: Запустить** полный набор — PASS.
- [ ] **Step 5: Коммит** `feat(setup): hardware-based configuration presets`.

### Task 6: Запись конфига

**Files:**
- Create: `setup/config_writer.py`
- Test: `tests/setup/test_config_writer.py`
- Docs: импакт `config-writer`

**Interfaces:**
- Consumes: `Preset`, `user_config_path`, `load_config`.
- Produces:
  - `build_config_data(preset: Preset, existing: dict[str, Any] | None = None) -> dict[str, Any]`:
    - задаёт `reflection.generator` и `reflection.critic` (`provider: ollama`, `name`, `base_url: http://localhost:11434/v1`, `think: false`; температура генератора 0.9, критика 0.1);
    - `reflection.language: auto`;
    - `context.max_total_tokens`;
    - остальные ключи `existing` сохраняются;
  - `write_config(data: dict[str, Any], path: Path) -> Path | None` — атомарная запись (`path.with_suffix(".yaml.tmp")` + `os.replace`). Возвращает путь `.bak`, если был старый файл.

- [ ] **Step 1: Тесты.**
  - `test_build_from_scratch_is_valid`: результат проходит `load_config(path)` после записи; модели совпадают с пресетом.
  - `test_build_keeps_unrelated_keys`: `existing` с `observability.langfuse.enabled: off`, `reflection.prompts.critic: x.md`, `reflection.max_iterations: 5` → всё сохранено (Review Focus 4).
  - `test_write_creates_bak`: второй вызов → `config.yaml.bak` равен первому содержимому.
  - `test_write_atomic_on_error`: monkeypatch `os.replace` бросает `OSError` → исходный файл не изменён, `.tmp` удалён.
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать** (`yaml.safe_dump(sort_keys=False, allow_unicode=True)`).
- [ ] **Step 4: Запустить** полный набор — PASS.
- [ ] **Step 5: Коммит** `feat(setup): atomic config writer with backup`.

### Task 7: Скачивание моделей

**Files:**
- Create: `setup/models.py`
- Test: `tests/setup/test_models.py`
- Docs: импакт `model-pull`

**Interfaces:**
- Consumes: `Preset`, `OllamaInfo`, `parse_ollama_ps`, `Runner`.
- Produces:
  - `missing_models(preset: Preset, installed: Sequence[str]) -> list[str]` — уникальные модели пресета, которых нет. Тег `:latest` сравнивается нормализованно;
  - `@dataclass(frozen=True) PullProgress(model: str, status: str, completed: int | None, total: int | None)`;
  - `class PullError(Exception)`;
  - `async pull(model: str, client: httpx.AsyncClient, base_url: str) -> AsyncIterator[PullProgress]` — `POST /api/pull {"model": m, "stream": true}`, построчный NDJSON. Строка с `"error"` → `PullError(текст)`; поток закончился без `status == "success"` → `PullError("interrupted")`. Отмена — через отмену задачи-потребителя;
  - `async verify(model: str, client, base_url, runner) -> list[Check]` — короткий `POST /api/generate {"model": m, "prompt": "ok", "stream": false, "options": {"num_predict": 1}}`, затем `ollama ps`. Проверяет `100% GPU` и `context >= ollama_context`; несоответствие → `warn`.

- [ ] **Step 1: Тесты.**
  - `test_missing_models_dedup`: `light` при пустом списке → `["qwen3:4b"]`.
  - `test_missing_models_latest`: `installed=["qwen3:4b"]` → `[]`; `"llama3"` и `"llama3:latest"` считаются одной моделью.
  - `test_pull_progress_sequence`: MockTransport отдаёт `pulling manifest` → `downloading` (`completed=50, total=100`) → `success` → итератор выдаёт 3 события.
  - `test_pull_error_line`: `{"error":"pull model manifest: file does not exist"}` → `PullError` с этим текстом (Review Focus 3).
  - `test_pull_interrupted`: поток обрывается без `success` → `PullError("interrupted")`.
  - `test_verify_cpu_warns`: `ollama ps` с `100% CPU` → check `warn`.
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать** (`client.stream("POST", ..., timeout=None)`, `aiter_lines`).
- [ ] **Step 4: Запустить** полный набор — PASS.
- [ ] **Step 5: Коммит** `feat(setup): pull configured Ollama models with progress`.

### Task 8: Установка и настройка Ollama

**Files:**
- Create: `setup/ollama_setup.py`, `setup/winenv.py`
- Test: `tests/setup/test_ollama_setup.py`
- Docs: `docs/troubleshooting.md` (Ollama), импакт `ollama-install`

**Interfaces:**
- Consumes: `downloads_dir`, `find_ollama_exe`, `Runner`.
- Produces:
  - `INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"`;
  - `@dataclass(frozen=True) DownloadProgress(done: int, total: int | None)`;
  - `async download_installer(client: httpx.AsyncClient, dest_dir: Path) -> AsyncIterator[DownloadProgress]` — пишет в `OllamaSetup.exe.part`, переименовывает по завершении. При исключении или отмене `.part` удаляется;
  - `launch_installer(path: Path, popen=subprocess.Popen) -> None` — без ожидания;
  - `async wait_for_server(client, base_url, timeout_s: float = 120, interval_s: float = 2, clock=time.monotonic, sleep=asyncio.sleep) -> bool`;
  - `recommended_env(preset: Preset) -> dict[str, str]` = `{"OLLAMA_CONTEXT_LENGTH": str(preset.ollama_context), "OLLAMA_FLASH_ATTENTION": "1", "OLLAMA_KV_CACHE_TYPE": "q8_0"}`;
  - `winenv.set_user_env(values: Mapping[str, str]) -> None` — `winreg` `HKEY_CURRENT_USER\Environment`, `REG_SZ`, затем `SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", SMTO_ABORTIFHUNG, 5000)`. На не-Windows бросает `NotImplementedError`;
  - `restart_ollama(runner: Runner, popen=subprocess.Popen, exe: Path | None) -> None` — `taskkill /IM "ollama app.exe" /F` и `taskkill /IM ollama.exe /F` (ненулевой код не ошибка), затем запуск `ollama app.exe` рядом с `exe`, иначе `ollama serve`;
  - `install_hint(os_name: str) -> str`:
    - Linux: `curl -fsSL https://ollama.com/install.sh | sh`;
    - macOS: `brew install ollama` или ссылка `https://ollama.com/download`.

- [ ] **Step 1: Тесты.**
  - `test_download_writes_file`: MockTransport отдаёт 3 чанка с `content-length` → события `done` растут, файл на месте, `.part` нет.
  - `test_download_cut_removes_part`: обрыв посреди потока → исключение, ни `.part`, ни `.exe`.
  - `test_wait_for_server_ok_after_retries`: первые два ответа `ConnectError`, третий 200 → `True`, `sleep` вызван 2 раза.
  - `test_wait_for_server_timeout`: фейковый `clock` → `False`.
  - `test_recommended_env_values`.
  - `test_restart_calls_taskkill_then_start`: записывающий runner/popen, порядок вызовов.
  - `test_set_user_env_windows` — `@pytest.mark.skipif(sys.platform != "win32")`: пишет `AGORA_TEST_VAR`, читает обратно через `winreg`, удаляет.
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать.**
- [ ] **Step 4: Запустить** полный набор (mypy: `winreg` и `ctypes.windll` под `if sys.platform == "win32":`) — PASS.
- [ ] **Step 5: Коммит** `feat(setup): download/launch Ollama installer and apply recommended settings`.

### Task 9: CLI — `agora doctor` и `agora setup`

**Files:**
- Create: `setup/cli.py`
- Modify: `__main__.py` — подкоманды
- Test: `tests/setup/test_cli.py`, `tests/test_main.py`
- Docs: `docs/start.md`, `docs/troubleshooting.md`, импакт `cli-doctor`

**Interfaces:**
- Consumes: `collect`, `load_presets`, `recommend`, `unmet`.
- Produces:
  - `format_report(report: SystemReport, presets: Sequence[Preset]) -> str` — строки `✓/⚠/✕ <name>: <detail>`, затем таблица пресетов с пометкой `(recommended)`;
  - `async doctor(network: bool = True, out: TextIO = sys.stdout, **collect_kwargs) -> int`, возвращает 0/1/2 по `report.worst`;
  - `__main__`:
    - `agora` без подкоманды — как сейчас;
    - `agora doctor [--no-network]`;
    - `agora setup` — запускает TUI сразу с мастером (`AgoraApp(..., start_wizard=True)`, см. Task 10);
    - `--version` остаётся.
  - При отсутствии конфига (`find_config_path(...) is None`) `main` передаёт `start_wizard=True`.

- [ ] **Step 1: Тесты.**
  - `test_doctor_exit_codes`: отчёты `ok`, `warn`, `error` → 0, 1, 2.
  - `test_format_report_marks_recommended`: строка с `quality` содержит `(recommended)`.
  - `test_main_doctor_no_network`: `main(["doctor", "--no-network"])` возвращает int, вывод содержит `OS`.
  - `test_main_first_run_starts_wizard`: monkeypatch `AgoraApp` → `start_wizard=True`, если `AGORA_HOME` пустой и нет `./config/agora.yaml`.
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать.** Если stdout не UTF-8 (cp1252/cp866), заменить символы на `[ok]/[!]/[x]`. Проверка: `sys.stdout.encoding`.
- [ ] **Step 4: Запустить** полный набор — PASS.
- [ ] **Step 5: Коммит** `feat(cli): agora doctor and agora setup`.

### Task 10: Мастер в TUI, F8, About

**Files:**
- Create: `tui/setup_wizard.py`
- Modify:
  - `tui/app.py` — параметр `start_wizard`, F8, применение нового конфига;
  - `tui/dialogs.py` — About в `HelpScreen`, `HELP_ROWS` + F8;
  - `tui/agora.tcss`.
- Test: `tests/tui/test_setup_wizard.py`, `tests/tui/test_snapshots.py`
- Docs: `docs/user-guide.md` (черновик раздела Setup), импакт `setup-wizard`

**Interfaces:**
- Consumes: всё из Tasks 4–8.
- Produces:
  - `@dataclass SetupDeps`:
    - `collect: Callable[[], Awaitable[SystemReport]]`;
    - `client_factory: Callable[[], httpx.AsyncClient]`;
    - `runner: Runner`;
    - `popen`;
    - `set_env: Callable[[Mapping[str, str]], None]`;
    - `config_path: Path`;
    - `base_url: str`;
    - `default_deps() -> SetupDeps`;
  - `SetupWizard(ModalScreen[Path | None])` — возвращает путь записанного конфига или `None` при Esc;
  - `AgoraApp.__init__(..., start_wizard: bool = False, setup_deps: SetupDeps | None = None)`;
  - после закрытия мастера с путём: `load_config(path)` → `rebuild_service` → `check_health()`;
  - `Binding("f8", "setup", "Setup", priority=True)`;
  - `HelpScreen` показывает `Agora {__version__} — https://github.com/cucumber405d/agora` и текущие модели.

Шаги мастера — один экран с `ContentSwitcher`, по шагу из спеки §4.4. Кнопки: `Next` (Enter), `Back`, `Skip`, `Retry` где уместно, `Esc` — выход без записи. Каждый шаг кнопками и стрелками управляется с клавиатуры (урок с ErrorScreen). Скачивание идёт в воркере `group="setup"`, Esc во время скачивания отменяет воркер. Сетевая ошибка → `ErrorScreen` с Retry/Skip.

- [ ] **Step 1: Тесты** (фейковые `SetupDeps`):
  - `test_wizard_happy_path`: отчёт 4070/12 ГБ, Ollama запущена, моделей нет → выделен `quality` → Next ×4 → фейковый pull вызван для `qwen3.5:9b` и `qwen3:14b` → файл конфига записан, главный экран показывает новые модели в статус-баре.
  - `test_wizard_skip_everything_still_writes_config`.
  - `test_wizard_installs_ollama`: `installed=False` → кнопка `Download and run installer` → вызван `popen` с путём `OllamaSetup.exe` → `wait_for_server` вернул `True` → переход дальше.
  - `test_wizard_cancel_download_cleans_up`: Esc во время скачивания → нет `.part`, мастер остаётся на шаге.
  - `test_wizard_network_error_shows_error_box` → Retry повторяет скачивание.
  - `test_wizard_disk_warning`: `free_disk_gb=5`, `quality` → видимое предупреждение.
  - `test_first_run_opens_wizard`: `start_wizard=True` → экран `SetupWizard` после монтирования.
  - `test_f8_opens_wizard`; `test_f8_blocked_during_run`.
  - `test_help_shows_version`.
  - Snapshots: `wizard_diagnostics`, `wizard_presets`.
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать.** Существующие snapshot-тесты футера обновить (появилась F8) и проверить глазами.
- [ ] **Step 4: Запустить** полный набор — PASS.
- [ ] **Step 5: Коммит** `feat(tui): first-run setup wizard (F8)`.

### Task 11: Сборка exe и установщик

**Files:**
- Create: `packaging/agora.spec`, `packaging/agora.iss`, `packaging/launch.cmd`, `packaging/entry.py`, `scripts/smoke.py`
- Modify: `pyproject.toml` (dev: `pyinstaller`), `__init__.py` — `__version__ = "0.2.0"`
- Test: `tests/test_packaging.py`
- Docs: `docs/start.md` (сборка локально), импакт `windows-installer`

**Interfaces:**
- Produces:
  - `packaging/entry.py`: `from ibikus.appa.agora.__main__ import main; raise SystemExit(main())`;
  - `scripts/smoke.py <path-to-agora.exe>` — запускает `--version` (ожидает `agora 0.2.0`) и `doctor --no-network` (код ∈ {0, 1, 2}, в stderr нет `Traceback`);
  - Inno Setup читает версию из `/DAppVersion=…`.

**Содержимое `agora.spec`:**
- `collect_data_files` для `ibikus.appa.agora` (шаблоны, tcss, `presets.yaml`), `markitdown`, `magika`, `pdfminer`;
- `collect_submodules("textual")`;
- `console=True`, `name="agora"`, onedir.

**Содержимое `agora.iss`:**
- `PrivilegesRequired=lowest`, `DefaultDirName={localappdata}\Programs\Agora`;
- `OutputBaseFilename=Agora-Setup-{#AppVersion}`;
- иконки `{userprograms}\Agora` → `launch.cmd`;
- `Tasks`: `desktopicon` (выключена по умолчанию), `addtopath`;
- `[Registry]` — PATH пользователя только при `addtopath`, удаление при деинсталляции;
- `[UninstallDelete]` — только `{app}`.

**`launch.cmd`:**

```bat
@echo off
where wt >nul 2>nul && (start "" wt -w new --title Agora "%~dp0agora.exe" & exit /b)
chcp 65001 >nul
mode con cols=160 lines=45
"%~dp0agora.exe" %*
```

- [ ] **Step 1: Тест `test_packaging.py`:**
  - `test_iss_version_matches`: `agora.iss` содержит `PrivilegesRequired=lowest`;
  - `test_spec_mentions_resources`: `agora.spec` перечисляет `presets.yaml`-пакет и `markitdown`;
  - `test_version_is_0_2_0`.
- [ ] **Step 2: Запустить** — FAIL; реализовать — PASS.
- [ ] **Step 3: Локальная сборка на Windows:** `uv run pyinstaller packaging/agora.spec --noconfirm`, затем `uv run python scripts/smoke.py dist/agora/agora.exe` — exit 0. Если Inno Setup установлен локально: `iscc /DAppVersion=0.2.0 packaging/agora.iss` → `Agora-Setup-0.2.0.exe`. Ручной прогон установки по чек-листу из Task 13.
- [ ] **Step 4: Коммит** `build: PyInstaller onedir and per-user Inno Setup installer`.

### Task 12: CHANGELOG и релиз в GitHub Actions

**Files:**
- Create: `scripts/changelog.py`, `.github/workflows/release.yml`
- Test: `tests/test_changelog.py`
- Docs: импакт `release-pipeline`

**Interfaces:**
- Produces:
  - `extract_en(markdown: str) -> str` — текст секции `## EN` до следующего `## `;
  - `build_changelog(impacts_dir: Path, since: date | None, version: str) -> str` — `## <version>` и по пункту на импакт: заголовок `# …` файла + EN-блок, по дате имени файла по возрастанию;
  - CLI: `python scripts/changelog.py --version 0.2.0 --since 2026-11-12 --out CHANGELOG.md`. `--since` берётся из даты предыдущего тега (`git log -1 --format=%as <prev-tag>`), если тега нет — все импакты.

**`release.yml`:**
- `on: push: tags: ["v*"]`;
- `runs-on: windows-latest`;
- шаги:
  1. checkout с `fetch-depth: 0`;
  2. setup-uv;
  3. `uv sync --frozen`;
  4. проверка `v$(python -c "import ibikus.appa.agora as a; print(a.__version__)") == $GITHUB_REF_NAME`;
  5. ruff, mypy, pytest;
  6. pyinstaller, `scripts/smoke.py`;
  7. `choco install innosetup -y`, `iscc /DAppVersion=…`;
  8. `Compress-Archive dist/agora → Agora-<ver>-portable.zip`;
  9. changelog → `CHANGELOG.md`;
  10. `gh release create $GITHUB_REF_NAME Agora-Setup-<ver>.exe Agora-<ver>-portable.zip --notes-file CHANGELOG.md`.
- `permissions: contents: write`.

- [ ] **Step 1: Тесты.**
  - `test_extract_en`.
  - `test_extract_en_missing_returns_empty`.
  - `test_build_changelog_since_filters_and_orders`: три файла с датами 11-09, 11-10, 11-12, `since=2026-11-10` → два пункта, по порядку.
- [ ] **Step 2: Запустить** — FAIL; реализовать — PASS.
- [ ] **Step 3: Проверить YAML:** `uv run python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/release.yml'))"` — без ошибок.
- [ ] **Step 4: Коммит** `ci: release workflow with installer, portable zip and changelog`.

### Task 13: Витрина и документация

**Files:**
- Create:
  - `README.md` (EN);
  - `docs/user-guide.md` (EN);
  - `docs/release-checklist.md`;
  - `scripts/screenshots.py`;
  - `docs/screenshots/*.png`.
- Modify: `docs/start.md`, `docs/architecture.md`, `docs/configuration.md`, `docs/troubleshooting.md`, `.gitignore` (`Claude outputs/`, `dist/`, `build/`, `*.spec.bak`)
- Docs: импакт `showcase-docs`

**Interfaces:**
- Consumes: снапшот-тесты (Tasks 3, 10).
- Produces: `scripts/screenshots.py` запускает `AgoraApp` с фейковым сервисом через `run_test`, сохраняет `app.save_screenshot()` для `main`, `wizard`, `llm-log`, `document-preview` в SVG и конвертирует в PNG через Playwright (`page.screenshot`).

**Содержимое:**
- **README:**
  - одно предложение о продукте;
  - скриншот главного экрана;
  - Features: reflection loop, documents, local by default, setup wizard;
  - Install — Windows: скачать `Agora-Setup-x.y.z.exe` из Releases → запустить → мастер; from source: `uv sync && uv run agora`;
  - SmartScreen note;
  - Keys (таблица F1–F10, Esc, Ctrl+PgUp);
  - Configuration (ссылка);
  - Architecture (ссылка);
  - License.
- **`user-guide.md`:** Files & documents, Keys, Presets, Setup wizard, `agora doctor`, Troubleshooting.
- **`release-checklist.md`:**
  1. новая учётка Windows;
  2. Setup.exe (SmartScreen → Run anyway);
  3. ярлык в «Пуске» открывает Windows Terminal;
  4. мастер: диагностика, пресет, Ollama, модели;
  5. PDF в контексте → Run → approved;
  6. `agora doctor` из нового терминала (PATH);
  7. удаление — `~/.agora` остался.
- **`architecture.md`:** модули `paths`, `context/documents`, `setup/*`, `tui/setup_wizard`, раздел Packaging.

- [ ] **Step 1:** Запустить `uv run python scripts/screenshots.py` — 4 PNG в `docs/screenshots/`. Открыть каждый и проверить глазами.
- [ ] **Step 2:** Написать документы. Проверить ссылки: `uv run python -c` с поиском `](docs/...)` и проверкой существования файлов — все существуют.
- [ ] **Step 3:** Полный набор проверок — PASS.
- [ ] **Step 4: Коммит** `docs: README, user guide, screenshots and release checklist`.

### Task 14: Финальная проверка и релиз 0.2.0

- [ ] **Step 1:** Полный набор: `uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest`, плюс `uv run pytest -m integration` с локальной Ollama (pull `qwen3:0.6b`, реальный PDF) — PASS.
- [ ] **Step 2:** Ревью всей ветки свежим ревьюером.
- [ ] **Step 3:** Пройти `docs/release-checklist.md` на машине пользователя с собранным локально Setup.exe.
- [ ] **Step 4:** По согласию пользователя — `git push`, `git tag v0.2.0 && git push origin v0.2.0`. Проверить, что workflow `Release` зелёный и в Release два файла.
