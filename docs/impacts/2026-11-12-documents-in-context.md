# 2026-11-12 — Documents in the context

## RU
- **Что изменилось:** в контекст можно отмечать PDF, DOCX, PPTX, XLSX и HTML. Они конвертируются в Markdown через markitdown, в промпте помечаются как `### file: x.pdf (converted from PDF)`. Новые причины пропуска: `legacy_format` (.doc/.xls/.ppt), `no_text` (например, скан без текстового слоя), `convert_failed`. Новые настройки `context.max_document_mb` (20) и `context.convert_timeout_s` (60). Результат конвертации кешируется по пути, времени изменения и размеру.
- **Зачем:** вопросы по собственным документам — основной сценарий; раньше принимались только текстовые файлы.
- **Влияние:** новые зависимости `markitdown[pdf,docx,pptx,xlsx]`, `psutil`; dev — `reportlab`, `python-docx`, `pillow` для фикстур. Если в своём `agora.yaml` задан `allowed_ext`, документы нужно добавить туда вручную.

## EN
- **What changed:** PDF, DOCX, PPTX, XLSX and HTML files can be marked for the context. They are converted to Markdown via markitdown and labelled `### file: x.pdf (converted from PDF)` in the prompt. New skip reasons: `legacy_format` (.doc/.xls/.ppt), `no_text` (e.g. a scan without a text layer), `convert_failed`. New settings `context.max_document_mb` (20) and `context.convert_timeout_s` (60). Conversions are cached by path, modification time and size.
- **Why:** asking questions about one's own documents is the main use case; only plain text files were accepted before.
- **Impact:** new dependencies `markitdown[pdf,docx,pptx,xlsx]`, `psutil`; dev: `reportlab`, `python-docx`, `pillow` for fixtures. A custom `allowed_ext` in your `agora.yaml` must list the document extensions explicitly.
