# Configuration

Sources, highest priority first:

1. Environment variables `AGORA_<SECTION>__<FIELD>` (e.g. `AGORA_REFLECTION__CRITIC__TEMPERATURE=0.2`)
2. YAML file: `--config PATH`, else `AGORA_CONFIG`, else `./config/agora.yaml`, else `~/.agora/config.yaml` (written by the setup wizard; `AGORA_HOME` moves `~/.agora`)
3. Built-in defaults

Partial overrides merge per field: setting only `reflection.critic.temperature` keeps the
critic's default provider and model. This applies only while the provider stays the default
one: when you switch a role to another provider, give its `name` (and `base_url` if needed)
explicitly; nothing is inherited from the old provider. Unknown fields are rejected.

Relative `reflection.prompts.*` paths are resolved against the current working directory.

## Fields

| Field | Default | Notes |
|---|---|---|
| `reflection.max_iterations` | `3` | 1-10 |
| `reflection.language` | `auto` | language of answers and critiques; `auto` detects Russian / German / English from the prompt, or give a name such as `German` |
| `reflection.approve_threshold` | `8` | 0-10; hard floor: a draft is accepted only if the critic approves **and** `score >= threshold` |
| `reflection.generator` | `ollama / qwen2.5:7b, t=0.9, base_url http://localhost:11434/v1` | model, see below |
| `reflection.critic` | `anthropic / claude-haiku-4-5, t=0.1` | model, see below |
| `reflection.prompts.generator` / `.critic` | built-in | path to a custom instruction file |
| `context.max_file_kb` | `256` | larger files are skipped |
| `context.max_total_tokens` | `32000` | cumulative budget, estimated as chars / 4 |
| `context.allowed_ext` | `.md .txt .py .java .yaml .json` | case-insensitive |
| `observability.langfuse.enabled` | `auto` | `auto` = on when keys are set; `on`; `off` |

### Model fields

| Field | Default | Notes |
|---|---|---|
| `provider` | - | `ollama`, `anthropic`, `openai`, `openrouter` |
| `name` | - | OpenRouter names need a vendor prefix, e.g. `openai/gpt-4o-mini` |
| `temperature` | - | 0-2 |
| `max_tokens` | none | |
| `base_url` | none | Ollama default `http://localhost:11434/v1`; OpenAI-compatible servers |
| `timeout_s` | `60` | per request |
| `max_retries` | `3` | SDK-level retries with backoff (429, 5xx, connection errors) |
| `think` | none | Ollama only. `false` disables the reasoning phase of thinking models (qwen3, qwen3.5): faster, and the context is not used up by reasoning. Unset keeps the model default. |

## Secrets

API keys are read only from the environment or `.env` (see `.env.example`), never from YAML:
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`,
`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`.

## Other environment variables

| Variable | Default | Purpose |
|---|---|---|
| `AGORA_HOME` | `~/.agora` | log directory root (`$AGORA_HOME/logs/agora.log`) |
| `AGORA_LOG_LEVEL` | `INFO` | log level |

## Fully local setup

```yaml
reflection:
  critic: {provider: ollama, name: qwen2.5:7b, temperature: 0.1}
```
