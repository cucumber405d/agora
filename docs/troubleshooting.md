# Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Invalid configuration: ... ANTHROPIC_API_KEY is not set`, exit code 2 | The default critic is Anthropic. Put the key into `.env`, or switch the critic to `provider: ollama` (see `configuration.md`). |
| `Invalid configuration: reflection.xxx: ...`, exit code 2 | Fix the named field in YAML or the matching `AGORA_*` variable. |
| Run feed shows `provider_error: ... connection` | Ollama is not running or `base_url` is wrong. Start it (`ollama serve`) and pull the model (`ollama pull qwen2.5:7b`). |
| `provider_error` with 401/403 | Wrong or expired API key. |
| `critic_invalid` | The critic model could not produce the structured verdict. Use a stronger critic model or lower its temperature. |
| Status line shows `Langfuse ✕` | `enabled: on` without keys, or Langfuse client failed to start; see the log. `○` means tracing is off. |
| Garbage or banner text in the terminal | Should not happen: logs and warnings go to `~/.agora/logs/agora.log`. Report it with the log. |
| `Ctrl+Enter` does nothing | Some terminals cannot send it; use `F2`. |
| `F5` copies nothing | Clipboard uses OSC 52; enable it in the terminal (Windows Terminal supports it). |

Logs: `~/.agora/logs/agora.log` (override with `AGORA_HOME`, level with `AGORA_LOG_LEVEL=DEBUG`).
