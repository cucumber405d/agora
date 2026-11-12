# 2026-11-12 — Setup wizard (F8)

## RU
- **Что изменилось:** мастер настройки из шести шагов: диагностика компьютера → выбор конфигурации (с рекомендацией и предупреждениями о нехватке VRAM или места) → Ollama (скачать и запустить установщик или запустить установленную) → рекомендуемые настройки Ollama с перезапуском → скачивание недостающих моделей с прогрессом → запись `~/.agora/config.yaml` и проверка модели (`100% GPU`, окно контекста). Открывается при первом запуске, по `F8` и командой `agora setup`. Esc во время скачивания отменяет только скачивание, иначе закрывает мастер без записи. Ошибки показываются красным внутри мастера с кнопками Retry и Skip. В справке (F1) появился блок About с версией, ссылкой на GitHub и текущими моделями.
- **Зачем:** человек без опыта получает работающую Agora без консоли и ручного редактирования YAML.
- **Влияние:** в футере появилась `F8 Setup`. Если в текущей папке есть `config/agora.yaml`, при старте он важнее `~/.agora/config.yaml` — мастер об этом предупреждает.

## EN
- **What changed:** a six-step setup wizard: computer diagnostics → configuration choice (with a recommendation and warnings about missing VRAM or disk space) → Ollama (download and run the installer, or start an installed one) → recommended Ollama settings with a restart → pulling missing models with progress → writing `~/.agora/config.yaml` and verifying the model (`100% GPU`, context window). It opens on the first start, with `F8` and with `agora setup`. Esc during a download cancels only the download; otherwise it closes the wizard without writing anything. Errors are shown in red inside the wizard with Retry and Skip. Help (F1) now has an About block with the version, the GitHub link and the current models.
- **Why:** a non-technical user gets a working Agora without a console or hand-edited YAML.
- **Impact:** the footer shows `F8 Setup`. A `config/agora.yaml` in the current folder still wins over `~/.agora/config.yaml` at startup; the wizard warns about that.
