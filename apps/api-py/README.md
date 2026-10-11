# Customer Compass API (Python)

FastAPI service for the v2 stack migration (replacing the Express API in
`apps/api`, one PR at a time — see `docs/v2-stack-migration.md`).

- **PR 2**: app wiring, Postgres connectivity check (`/health`), Docker image.
- **PR 3**: document ingestion pipeline (`POST /documents/ingest`) — parses
  `sample-data/documents/*.md`, chunks, embeds via Google's
  `gemini-embedding-001`, and stores chunk vectors + payload in Qdrant.
  Postgres keeps `documents`/`ingestion_runs` as ingestion metadata only.

No chat/RAG query routes are ported yet — `apps/api` (Express) remains the
one actually used by the frontend until that migration completes.

## Local development

```bash
cd apps/api-py
uv sync                 # installs dependencies into .venv
cp .env.example .env    # then edit: DATABASE_URL, QDRANT_URL, GOOGLE_API_KEY
uv run uvicorn app.main:app --reload --port 8001
```

Requires Postgres and Qdrant running: `docker-compose up -d db qdrant` (from
the repo root). Get a free `GOOGLE_API_KEY` at
https://aistudio.google.com/apikey — needed for `/documents/ingest` (not for
`/health`).

## Verify

```bash
curl -s http://localhost:8001/health
# {"status":"ok"}

curl -s -X POST http://localhost:8001/documents/ingest
# {"ingestionRunId":1,"documentsProcessed":8,"chunksCreated":16,"status":"completed"}

curl -s http://localhost:8001/documents
curl -s http://localhost:8001/documents/ingestion-runs
```

## Tests

```bash
uv run pytest
```

`tests/test_ingest.py` is skipped automatically if `GOOGLE_API_KEY` isn't set
in the environment (it needs a live embedding call).
