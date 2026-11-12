# 2026-11-12 — Installing and configuring Ollama

## RU
- **Что изменилось:** `setup/ollama_setup.py` скачивает официальный `OllamaSetup.exe` с прогрессом (через файл `.part`, при обрыве или отмене ничего не остаётся), запускает его, ждёт сервер до 120 с, формирует рекомендуемые переменные (`OLLAMA_CONTEXT_LENGTH` по конфигурации, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`) и перезапускает Ollama. `setup/winenv.py` пишет переменные в `HKCU\Environment` без прав администратора. Для Linux/macOS — команда установки.
- **Зачем:** человек без опыта должен получить работающую Ollama, не открывая консоль.
- **Влияние:** пока только API; используется мастером. Раздел в `docs/troubleshooting.md`.

## EN
- **What changed:** `setup/ollama_setup.py` downloads the official `OllamaSetup.exe` with progress (via a `.part` file; a failed or cancelled download leaves nothing behind), launches it, waits up to 120 s for the server, builds the recommended variables (`OLLAMA_CONTEXT_LENGTH` from the preset, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`) and restarts Ollama. `setup/winenv.py` writes the variables to `HKCU\Environment` without administrator rights. Linux/macOS get the install command.
- **Why:** a non-technical user must end up with a working Ollama without opening a console.
- **Impact:** API only; used by the wizard. New section in `docs/troubleshooting.md`.
