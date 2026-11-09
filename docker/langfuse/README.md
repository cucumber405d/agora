# Langfuse (self-hosted) for Agora

```bash
docker compose -f docker/langfuse/compose.yaml up -d
```

1. Open http://localhost:3000, sign up (local account), create an organization and a project.
2. In the project settings create API keys.
3. Put them into `.env` in the Agora root:

   ```
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=http://localhost:3000
   ```

4. Start `uv run agora`. The status line shows `Langfuse ●` when tracing is on.

Each run appears as a `reflection-run` trace with `iteration-N/generate` and
`iteration-N/critique` spans and one generation per model call.

For anything beyond local use, change every value marked `CHANGEME` in `compose.yaml`
(override via env, e.g. `ENCRYPTION_KEY=$(openssl rand -hex 32)`).

Stop: `docker compose -f docker/langfuse/compose.yaml down` (add `-v` to delete data).
