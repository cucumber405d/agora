# 2026-11-12 — User config in ~/.agora

## RU
- **Что изменилось:** если нет `--config`, `AGORA_CONFIG` и `./config/agora.yaml`, Agora читает `~/.agora/config.yaml` (или `$AGORA_HOME/config.yaml`). Пути пользователя собраны в модуле `paths.py`.
- **Зачем:** установленное приложение запускается не из папки проекта; конфиг, созданный мастером настройки, должен находиться всегда.
- **Влияние:** прежний порядок не изменился, добавлен только последний шаг. Тесты больше не могут случайно прочитать настоящий `~/.agora`.

## EN
- **What changed:** when there is no `--config`, `AGORA_CONFIG` or `./config/agora.yaml`, Agora reads `~/.agora/config.yaml` (or `$AGORA_HOME/config.yaml`). User locations live in the new `paths.py` module.
- **Why:** an installed app is not started from the project folder; the config written by the setup wizard must always be found.
- **Impact:** the existing order is unchanged, only a last step is added. Tests can no longer accidentally read the real `~/.agora`.
