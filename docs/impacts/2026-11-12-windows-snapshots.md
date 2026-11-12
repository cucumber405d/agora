# 2026-11-12 — UI snapshots on Windows

## RU
- **Что изменилось:** разделитель в сокращённом заголовке панели файлов (`Files: …\project`) вынесен в константу; в тестах-снапшотах он фиксирован как `/`, поэтому SVG-снапшоты, записанные на Linux, совпадают и на Windows. CI на Windows при падении выкладывает `snapshot_report.html` как артефакт.
- **Зачем:** первый прогон CI на Windows упал на всех восьми снапшотах из-за `\` вместо `/` в заголовке.
- **Влияние:** в самом приложении на Windows по-прежнему показывается `\`.

## EN
- **What changed:** the separator in the shortened files panel title (`Files: …\project`) is now a module constant; snapshot tests pin it to `/`, so SVG snapshots recorded on Linux also match on Windows. On failure the Windows CI job uploads `snapshot_report.html` as an artifact.
- **Why:** the first Windows CI run failed all eight snapshots because of `\` instead of `/` in the title.
- **Impact:** the app itself still shows `\` on Windows.
