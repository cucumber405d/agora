# 2026-11-12 — README, user guide and screenshots

## RU
- **Что изменилось:** добавлены `README.md` (назначение, скриншоты, установка в два шага, предупреждение SmartScreen, клавиши, ссылки), `docs/user-guide.md` (экран, файлы и документы, конфигурации, мастер, диагностика), `docs/release-checklist.md` (ручная проверка релиза на чистой учётной записи) и скриншоты в `docs/screenshots/`, которые генерирует `scripts/screenshots.py` из настоящего интерфейса с фейковыми моделями. `docs/architecture.md` описывает новые модули и сборку.
- **Зачем:** проект должен быть понятен с первого взгляда — для показа и для тех, кто его скачает.
- **Влияние:** описание пакета в `pyproject.toml` теперь берётся из `README.md`.

## EN
- **What changed:** added `README.md` (purpose, screenshots, two-step install, SmartScreen note, keys, links), `docs/user-guide.md` (screen, files and documents, configurations, wizard, diagnostics), `docs/release-checklist.md` (manual release check on a clean user account) and screenshots in `docs/screenshots/`, rendered by `scripts/screenshots.py` from the real UI with fake models. `docs/architecture.md` covers the new modules and the build.
- **Why:** the project must be clear at first sight, for demos and for people who download it.
- **Impact:** the package description in `pyproject.toml` now comes from `README.md`.
