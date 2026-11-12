# Agora user guide

## The screen

- **Files** (left top): the folder Agora was started in. Mark files for the context with `Space`, `Ins` or a click on `[ ]`. `..`, `Backspace` and `Ctrl+PgUp` go to the parent folder; `Ctrl+R` re-reads the folder. The panel subtitle shows how many files and tokens the context holds.
- **Progress** (left bottom): the models, loop limits and each stage with its duration. `Ctrl+L` hides or shows it.
- **Prompt** (right top): your request. `F2` or `Ctrl+Enter` starts a run.
- **Run** (right middle): each iteration with its draft and critique, then the final answer with the chosen iteration and score.
- **LLM log** (right bottom): every request and response (cyan requests, white responses, yellow retries, red errors). `Enter` opens the full text.

## Files and documents

Text files (`.md .txt .py .java .yaml .json`) are sent as they are. Documents are converted to Markdown first:

| Format | Notes |
|---|---|
| PDF | Text layer only; scans without text are skipped as `no_text` (OCR is not supported) |
| DOCX, PPTX, XLSX | Headings, lists and tables are kept as Markdown |
| HTML, HTM | Converted to Markdown |
| DOC, XLS, PPT | Not supported (`legacy_format`); save them as DOCX/XLSX/PPTX |

Large documents take a few seconds to convert. Progress shows `Context: converting N/M`, and a run waits for the conversion. Converted text is cached until the file changes. `Enter` on a file shows the extracted text and its token estimate. `agora convert FILE` prints the same text in a console.

Files that do not fit are reported as "Not sent" with a reason:
- `too_large`: over `max_file_kb` for text files, or `max_document_mb` for documents;
- `over_budget`: the context token budget is used up;
- `extension`, `not_utf8`, `convert_failed`: the file type is not allowed, is not UTF-8 text, or could not be converted.

## Configurations

The setup wizard offers three configurations and recommends the strongest one your computer runs well:

| Configuration | For | Models | Download |
|---|---|---|---|
| Light | any PC with 8 GB RAM, also without a GPU | qwen3:4b / qwen3:4b | ~2.5 GB |
| Standard | NVIDIA GPU with 8 GB | qwen3.5:9b / qwen3:8b | ~11 GB |
| Quality | NVIDIA GPU with 12 GB | qwen3.5:9b / qwen3:14b | ~15 GB |

For other GPUs the memory cannot be measured, so you choose yourself. `F9` switches models for the current session only. The configuration file is `~/.agora/config.yaml` (see [configuration](configuration.md)).

## Setup wizard

It opens on the first start, with `F8`, or with `agora setup`.

1. **System:** OS, RAM, free disk space, GPU and Ollama state.
2. **Configuration:** pick one. Missing requirements are shown next to each.
3. **Ollama:** downloads and starts the official installer, or starts an installed Ollama.
4. **Ollama settings:** context window, flash attention and KV cache, written as user environment variables. Ollama is restarted.
5. **Models:** downloads the missing models with progress. `Esc` cancels; the next download resumes.
6. **Done:** writes the config, keeps the previous file as `config.yaml.bak`, and checks that the model loads fully on the GPU with the right context window.

Every step can be skipped. The red error box then tells you what is still missing when you run.

## Diagnostics

`agora doctor` prints the same checks as the wizard plus the configuration file in use. Its exit code is 0, 1 or 2. Logs are in `~/.agora/logs/agora.log`. More help: [troubleshooting](troubleshooting.md).
