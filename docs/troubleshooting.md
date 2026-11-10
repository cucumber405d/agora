# Troubleshooting

At start-up (after F9 and after a `provider_error`) Agora probes the configured LLMs and opens
a red **LLM not available** box when something is missing. It lists each problem with the
affected role (Generator / Critic) and a hint; **Retry** probes again, **Models (F9)** lets you
switch to another model, **Close** (or Esc) keeps working.

| Symptom | Cause / fix |
|---|---|
| Box: `Ollama is not reachable at http://localhost:11434` | Ollama is not installed or not running. Install it from https://ollama.com, start it (`ollama serve` or the tray app), then **Retry**. From WSL with Ollama on Windows, set `base_url` to the Windows host IP. |
| Box: `Model 'qwen2.5:7b' is not available in Ollama` | Run `ollama pull qwen2.5:7b`, then **Retry**. |
| Box: `ANTHROPIC_API_KEY was rejected (HTTP 401)` | The key in `.env` is wrong or revoked. |
| Box: `No connection to api.anthropic.com` | No internet access or a proxy blocks the API. |
| `Invalid configuration: ... ANTHROPIC_API_KEY is not set`, exit code 2 | The default critic is Anthropic. Put the key into `.env`, or switch the critic to `provider: ollama` (see `configuration.md`). |
| `Invalid configuration: reflection.xxx: ...`, exit code 2 | Fix the named field in YAML or the matching `AGORA_*` variable. |
| Run feed shows `provider_error: ... connection` | Ollama is not running or `base_url` is wrong. Start it (`ollama serve`) and pull the model (`ollama pull qwen2.5:7b`). |
| `provider_error` with 401/403 | Wrong or expired API key. |
| Feed: `critique failed: …`, final status `critic_failed` | The critic model could not produce a valid verdict even with the JSON schema; the run keeps the latest (ungraded) draft. Use a stronger or different critic model (e.g. `llama3.1:8b`, `qwen2.5:14b`) or a cloud model. |
| Status line shows `Langfuse ✕` | `enabled: on` without keys, or Langfuse client failed to start; see the log. `○` means tracing is off. |
| Garbage or banner text in the terminal | Should not happen: logs and warnings go to `~/.agora/logs/agora.log`. Report it with the log. |
| `Ctrl+Enter` does nothing | Some terminals cannot send it; use `F2`. |
| `F5` copies nothing | Clipboard uses OSC 52; enable it in the terminal (Windows Terminal supports it). |

Logs: `~/.agora/logs/agora.log` (override with `AGORA_HOME`, level with `AGORA_LOG_LEVEL=DEBUG`).
