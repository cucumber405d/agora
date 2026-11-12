# 2026-11-12 — Document conversion in the UI

## RU
- **Что изменилось:** контекст теперь собирается в фоне: отметка большого PDF не замораживает интерфейс, а в панели Progress видно `Context: converting N/M`. Запуск (F2) сначала дожидается конвертации. Enter на файле в панели файлов открывает превью того, что уйдёт в модель: извлечённый текст и оценку токенов, а для пропущенного файла — причину.
- **Зачем:** конвертация документов может занимать секунды; пользователю нужно видеть, что извлеклось из PDF, до запуска.
- **Влияние:** подпись `Context: N files` обновляется с небольшой задержкой. Повторная конвертация того же файла берётся из кеша.

## EN
- **What changed:** the context is now built in the background: marking a large PDF no longer freezes the UI, and the Progress panel shows `Context: converting N/M`. A run (F2) waits for the conversion first. Enter on a file in the files panel previews what will be sent to the model: the extracted text and its token estimate, or the skip reason.
- **Why:** document conversion can take seconds; users need to see what was extracted from a PDF before running.
- **Impact:** the `Context: N files` label updates with a short delay. Converting the same file again is served from the cache.
