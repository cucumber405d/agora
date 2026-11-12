# 2026-11-12 — System diagnostics

## RU
- **Что изменилось:** новый модуль `setup/diagnostics.py` собирает сведения о системе: ОС, RAM, свободное место на диске моделей Ollama, видеокарту (NVIDIA — название и VRAM через `nvidia-smi`, остальные на Windows — только название), состояние Ollama (установлена, запущена, версия, скачанные модели, переменные `OLLAMA_*`). Каждая проверка независима: сбой одной даёт предупреждение, остальные выполняются.
- **Зачем:** основа для мастера первого запуска и `agora doctor` — подобрать конфигурацию под «железо» и объяснить, чего не хватает.
- **Влияние:** пока только API; в интерфейсе появится вместе с мастером. Внешние команды выполняются с таймаутом 10 с.

## EN
- **What changed:** the new `setup/diagnostics.py` module collects system facts: OS, RAM, free space on the Ollama models disk, the GPU (NVIDIA: name and VRAM via `nvidia-smi`; others on Windows: name only) and the Ollama state (installed, running, version, pulled models, `OLLAMA_*` variables). Every check is independent: one failing check yields a warning and the others still run.
- **Why:** the basis for the first-run wizard and `agora doctor`: pick a configuration that fits the hardware and explain what is missing.
- **Impact:** API only for now; it reaches the UI with the wizard. External commands run with a 10 s timeout.
