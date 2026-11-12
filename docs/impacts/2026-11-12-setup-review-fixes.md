# 2026-11-12 — Setup fixes after review

## RU
- **Что изменилось:**
  - Мастер ищет `ollama.exe` при каждом использовании: после свежей установки Ollama «Apply recommended» больше не останавливает Ollama без возможности её запустить (перезапуск проверяет наличие exe до `taskkill`).
  - Требования конфигураций учитывают реальные цифры: RTX 4070 (12282 МиБ) получает Quality, 8-гигабайтные карты — Standard, ноутбук с «8 ГБ» (7,8 ГБ) — Light.
  - Если сервер не появился после установщика, мастер предлагает «Check again», а не повторную установку.
  - `ollama serve`, запущенный из Agora, не пишет в терминал и не умирает вместе с ним.
  - Неожиданная ошибка в шаге мастера показывается красной строкой, приложение не закрывается; не-JSON ответ `/api/pull` — понятная ошибка.
  - Документы разрешены всегда, даже если в старом конфиге `allowed_ext` перечисляет только текст.
  - CI гоняет проверки, сборку exe и smoke-тест на Windows при каждом push.
- **Зачем:** находки финального ревью; главный путь нового пользователя Windows (установка Ollama → настройки) ломался.
- **Влияние:** сообщение «GPU memory could not be determined» показывается только когда память видеокарты действительно неизвестна.

## EN
- **What changed:**
  - The wizard looks up `ollama.exe` on every use: after a fresh Ollama install "Apply recommended" no longer stops Ollama without a way to start it (the restart checks for the exe before `taskkill`).
  - Preset requirements allow for real numbers: an RTX 4070 (12282 MiB) gets Quality, 8 GB cards get Standard, an "8 GB" laptop (7.8 GB) gets Light.
  - When the server does not appear after the installer, the wizard offers "Check again" instead of reinstalling.
  - `ollama serve` started from Agora no longer writes into the terminal or dies with it.
  - An unexpected error in a wizard step shows as a red status line instead of closing the app; a non-JSON `/api/pull` answer is a clear error.
  - Documents are always allowed, even when an older config lists only text types in `allowed_ext`.
  - CI runs the checks, the exe build and the smoke test on Windows on every push.
- **Why:** findings of the final review; the main path of a new Windows user (install Ollama → settings) was broken.
- **Impact:** "GPU memory could not be determined" is shown only when the GPU memory is really unknown.
