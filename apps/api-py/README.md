# Customer Compass API (Python)

FastAPI service for the v2 stack migration (replacing the Express API in
`apps/api`, one PR at a time — see `docs/v2-stack-migration.md`). This PR
only adds the skeleton: app wiring, Postgres connectivity check, Docker
image. No real routes (chat/RAG/CRM) are ported yet — `apps/api` (Express)
remains the one actually used by the frontend until that migration
completes.

## Local development

```bash
cd apps/api-py
uv sync                 # installs dependencies into .venv
cp .env.example .env    # then edit if your DATABASE_URL differs
uv run uvicorn app.main:app --reload --port 8001
```

## Verify

```bash
curl -s http://localhost:8001/health
# {"status":"ok"}  (requires Postgres running: docker-compose up -d db)
```

## Tests

```bash
uv run pytest
```
