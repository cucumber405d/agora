# 2026-11-12 — Windows build and installer

## RU
- **Что изменилось:** сборка через PyInstaller (`packaging/agora.spec`, режим onedir, `dist/agora/agora.exe`) и установщик Inno Setup (`packaging/agora.iss`): установка только для текущего пользователя в `%LOCALAPPDATA%\Programs\Agora` без прав администратора, ярлык в «Пуске» (по желанию — на рабочем столе), по желанию — добавление в PATH. Ярлык запускает `launch.cmd`: Windows Terminal, а если его нет — консоль 160×45 в UTF-8. Деинсталлятор не трогает `~/.agora` и модели Ollama. Новая команда `agora convert FILE` печатает извлечённый из документа текст; `scripts/smoke.py` проверяет собранный exe (`--version`, `doctor`, конвертация PDF/DOCX/XLSX). Версия 0.2.0; в `pyproject.toml` она берётся из `__version__`.
- **Зачем:** Agora должна ставиться и запускаться как обычная программа, без Python и uv.
- **Влияние:** в сборку входят метаданные всех зависимостей (иначе `genai_prices` падает при импорте). Установщик не подписан — Windows SmartScreen покажет предупреждение.

## EN
- **What changed:** a PyInstaller build (`packaging/agora.spec`, onedir, `dist/agora/agora.exe`) and an Inno Setup installer (`packaging/agora.iss`): per-user install into `%LOCALAPPDATA%\Programs\Agora` without administrator rights, a Start menu shortcut (desktop optional), optional PATH entry. The shortcut runs `launch.cmd`: Windows Terminal, or a 160×45 UTF-8 console without it. The uninstaller leaves `~/.agora` and Ollama models alone. New command `agora convert FILE` prints the text extracted from a document; `scripts/smoke.py` checks a built exe (`--version`, `doctor`, PDF/DOCX/XLSX conversion). Version 0.2.0; `pyproject.toml` now reads it from `__version__`.
- **Why:** Agora must install and start like a regular program, without Python or uv.
- **Impact:** the build ships the metadata of all dependencies (otherwise `genai_prices` fails on import). The installer is unsigned, so Windows SmartScreen shows a warning.
