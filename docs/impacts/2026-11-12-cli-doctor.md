# 2026-11-12 — agora doctor and agora setup

## RU
- **Что изменилось:** подкоманды `agora doctor [--no-network]` (диагностика в консоли, коды возврата 0/1/2, перечень подходящих конфигураций и найденный конфиг) и `agora setup` (открывает TUI сразу с мастером). При первом запуске без конфига Agora стартует с встроенной лёгкой конфигурацией и сразу открывает мастер вместо ошибки «ANTHROPIC_API_KEY is not set». Если консоль не UTF-8, вместо ✓/⚠/✕ печатается `[ok]/[!]/[x]`.
- **Зачем:** понятная диагностика у другого человека и запуск «из коробки».
- **Влияние:** запуск с существующим конфигом не изменился.

## EN
- **What changed:** new subcommands `agora doctor [--no-network]` (console diagnostics, exit codes 0/1/2, the configurations that fit and the config file found) and `agora setup` (opens the TUI with the wizard). On the first start without a config Agora starts with the built-in Light configuration and opens the wizard instead of failing with "ANTHROPIC_API_KEY is not set". Non-UTF-8 consoles get `[ok]/[!]/[x]` instead of ✓/⚠/✕.
- **Why:** clear diagnostics on someone else's machine and an out-of-the-box first start.
- **Impact:** starting with an existing config is unchanged.
