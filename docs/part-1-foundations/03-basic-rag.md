# Stage 3 — Basic RAG

**Part:** I — Foundations
**Status:** Completed

> **v2 stack note:** this record describes the original v1 implementation
> (Express API on port 3001, Ollama `mxbai-embed-large` embeddings, pgvector).
> In v2 the API is FastAPI (`apps/api-py`, port 8001, `/api/v1/...`,
> files `app/rag/*.py`), embeddings are Google `gemini-embedding-001`
> (768-dim) and vectors live in Qdrant. See
> [../architecture.md](../architecture.md) and [../tech-stack.md](../tech-stack.md).
> Paths, ports, models and curl examples below are kept as originally recorded.

## Goal

Build a transparent Retrieval-Augmented Generation pipeline using synthetic CRM
documents. The output must be grounded and cite its source chunks.

## Concepts: embeddings, semantic search, cosine similarity

This stage leans on a few terms that show up throughout the rest of the docs
(`embedding`, `semantic search`, `cosine similarity`, `vector`) without
re-explaining them every time. Here's what they mean, in plain language.

**Embedding** — a numerical fingerprint of meaning. An embedding model reads a
piece of text and outputs a fixed-length list of numbers (a *vector*) — this
app uses Ollama's `mxbai-embed-large`, which outputs 1024 numbers per chunk.
Texts with similar *meaning* produce vectors that point in similar
directions, even if they don't share any of the same words.

```text
"Can we set alerts per customer?"        -> [0.12, -0.08, 0.44, ... ]  (1024 numbers)
"Does the plan support per-client alarms?" -> [0.14, -0.07, 0.41, ... ]  (close by)
"What's the invoice due date?"             -> [-0.51, 0.33, 0.02, ... ]  (far away)
```

**Semantic search** — searching by *meaning* instead of by matching exact
keywords. A traditional keyword search for "alerts per customer" would miss a
document that says "per-client alarms" — no shared words. Semantic search
finds it anyway, because the two phrases embed to nearby vectors. This is
what makes RAG retrieval work here: the question and every document chunk are
embedded into the same vector space, and "relevant" is redefined as "nearby
in that space."

**Cosine similarity** — the specific way "nearby" is measured. Instead of
measuring the straight-line distance between two vectors, cosine similarity
measures the *angle* between them — it asks "do these two vectors point in
the same direction?", not "are these two points close together?". The result
is always between -1 (opposite meaning) and 1 (identical meaning); this app
treats anything below 0.3 as not relevant enough to cite (see
`MIN_SIMILARITY` in `apps/api/src/rag/retrieve.ts`).

```text
          ▲
          │      • question embedding
          │     ╱
          │    ╱  θ (small angle → high similarity)
          │   ╱
          │  • relevant chunk embedding
          │
          │              • unrelated chunk embedding
          │             (large angle → low similarity)
          └──────────────────────────────────────────▶
```

Postgres computes this directly on stored vectors via `pgvector`'s `<=>`
operator (`1 - (dc.embedding <=> $1) AS similarity` in `retrieve.ts`) — no
separate vector database is needed; the embeddings live in a normal
`document_chunks` table column.

## Implemented design

```text
Document -> parse (frontmatter + body) -> chunk (600 chars, 100 overlap)
         -> embed (Ollama mxbai-embed-large, 1024-dim) -> store (pgvector)
Question -> embed -> cosine similarity search (<=>) -> top chunks (>= 0.3 similarity)
         -> numbered context block -> LLM (grounded system prompt) -> answer + citations
```

- Vector storage: `pgvector` extension inside the existing PostgreSQL service
  (image switched to `pgvector/pgvector:pg17`). No ANN index yet — the corpus
  is small enough for an exact `<=>` scan; Stage 6 revisits indexing.
- Embeddings: local Ollama model `mxbai-embed-large`, called through
  `apps/api/src/rag/embeddings.ts`.
- Chunking: explicit character-based sliding window in
  `apps/api/src/rag/chunking.ts` (`CHUNK_SIZE=600`, `CHUNK_OVERLAP=100`),
  unit-tested in `chunking.test.ts`.
- Ingestion (`apps/api/src/rag/ingest.ts`): reads every `.md` file in
  `sample-data/documents/`, parses YAML frontmatter (`title`, `type`,
  optional `company`) with `gray-matter`, resolves `company` to an existing
  `companies.id`, truncates and re-inserts `documents`/`document_chunks` on
  each run, and records each run in `ingestion_runs`.
- Retrieval (`apps/api/src/rag/retrieve.ts`): embeds the question, runs a
  cosine-similarity query joining `document_chunks` → `documents` →
  `companies`, and builds a numbered, citable context block.
- Routes:
  - `POST /api/documents/ingest` — runs the full pipeline.
  - `GET /api/documents` — lists ingested documents with chunk counts.
  - `GET /api/documents/ingestion-runs` — ingestion history/debugging.
  - `POST /api/chat/rag` — grounded chat; returns `{ message, citations[] }`.
  - `POST /api/chat` — unchanged general chat from Stage 2 (now its own router).
- UI: an "Ingest documents" button, a "Use document knowledge (RAG)" toggle,
  and numbered citations (title, company, doc type, similarity score) shown
  under grounded answers.

Synthetic documents (`sample-data/documents/`) cover emails, call notes,
support conversations, and two product/service overviews, cross-referenced
with the three companies already in the CRM database — this sets up Stage 5's
DB + RAG linkage.

## Learning boundaries

- Explain and implement chunk size, overlap, embeddings, similarity scoring,
  retrieval, context construction, and citations explicitly.
- Keep document ingestion distinct from query-time retrieval.
- Add a way to inspect chunks and retrieved sources for debugging.
- Do not use tools/agent loops or hide the pipeline behind a broad framework.

## Acceptance criteria

A developer can ingest sample documents, ask a document-supported question, see
the answer’s citations, and verify the cited source text.

Verified: ingested 8 documents into 16 chunks; asked "Does the Fleet
Visibility package include alerting, and can alerts be set per customer?"
through `POST /api/chat/rag` and received a correct, cited answer referencing
the product overview and the matching support conversation.

## How to run the app

```bash
cd /home/devarapallim/Murali/git-personal/customer-compass
docker compose up -d db ollama
```

- **First time / fresh volume**: `db/init.sql` and `db/002-rag.sql` both run
  automatically (mounted as ordered init scripts).
- **Existing volume from before Stage 3** (already had `companies`,
  `contacts`, `deals`, `interactions`): the container image changes to
  `pgvector/pgvector:pg17`, but Postgres init scripts only run once against an
  empty data directory, so apply the new schema manually:

  ```bash
  docker exec -i customer-compass-db psql -U customer_compass -d customer_compass < db/002-rag.sql
  ```

Pull the models (once), then install and start the app:

```bash
docker exec customer-compass-ollama ollama pull qwen2.5:3b        # Stage 2 chat model
docker exec customer-compass-ollama ollama pull mxbai-embed-large # Stage 3 embedding model
npm install
npm run dev
```

This runs the API (`http://localhost:3001`) and the web UI
(`http://localhost:5173`) together.

## How to test manually

1. **API health check**
   ```bash
   curl -s http://localhost:3001/health
   # expect: {"status":"ok"}
   ```
2. **Ingest the sample documents**
   ```bash
   curl -s -X POST http://localhost:3001/api/documents/ingest | python3 -m json.tool
   ```
   Observe: `"status": "completed"`, `"documentsProcessed": 8`,
   `"chunksCreated": 16`. Then inspect what was stored:
   ```bash
   curl -s http://localhost:3001/api/documents | python3 -m json.tool
   ```
   Observe: 8 documents, each with `chunk_count: 2`, and `company_name` set for
   the 6 company-specific documents (`null` for the 2 product overviews).
3. **Ask a grounded question**
   ```bash
   curl -s -X POST http://localhost:3001/api/chat/rag \
     -H "Content-Type: application/json" \
     -d '{"messages":[{"role":"user","content":"Does the Fleet Visibility package include alerting, and can alerts be set per customer?"}]}' \
     | python3 -m json.tool
   ```
   Observe:
   - `message` answers the question and includes bracketed citation markers
     like `[1]`, `[2]`.
   - `citations` is a non-empty array; each entry's `title`/`snippet` should
     plausibly support the claim in `message` (expect the "Fleet Visibility
     rollout package overview" and "Pre-sales support conversation on alerting
     limits" documents to appear with high `similarity`, roughly 0.7–0.85).
4. **Confirm ungrounded chat still works unaffected**
   ```bash
   curl -s -X POST http://localhost:3001/api/chat \
     -H "Content-Type: application/json" \
     -d '{"messages":[{"role":"user","content":"Say hi in 5 words."}]}'
   ```
   Observe: a `message` field with no `citations` key.
5. **Browser walkthrough** — open `http://localhost:5173`:
   - The chat panel shows an "Ingest documents" button and a "Use document
     knowledge (RAG)" checkbox.
   - Click "Ingest documents" and observe the status line report documents and
     chunks ingested (matches step 2).
   - With the RAG checkbox **unchecked**, ask a general question — answered with
     no citations shown.
   - With the RAG checkbox **checked**, ask the Fleet Visibility question from
     step 3 — the assistant's reply should appear with a numbered citations list
     underneath it (title, company, doc type, similarity score).

## Inspecting the database with a visual tool

The CRM tables (`companies`, `contacts`, `deals`, `interactions`) and the RAG
tables (`documents`, `document_chunks`, `ingestion_runs`) all live in the
**same** `customer_compass` Postgres database (started via `docker-compose
up`) — there are not two separate databases to connect to.

Any Postgres client works (DBeaver, TablePlus, Adminer, `psql`). Connection
details:

| Field | Value |
| --- | --- |
| Host | `localhost` |
| Port | `5432` |
| Database | `customer_compass` |
| Username | `customer_compass` |
| Password | `customer_compass_dev` |
| SSL | disabled (local dev only) |

Quick CLI alternative:

```bash
docker exec -it customer-compass-db psql -U customer_compass -d customer_compass
```

```sql
\dt                          -- list all tables (CRM + RAG together)
SELECT * FROM documents;
SELECT id, document_id, chunk_index, left(content, 50) FROM document_chunks LIMIT 5;
SELECT * FROM ingestion_runs ORDER BY id DESC LIMIT 5;
```

## Developer note

Changed/added files:

- `docker-compose.yml` — `db` image switched to `pgvector/pgvector:pg17`;
  mounts `db/002-rag.sql`.
- `db/002-rag.sql` — pgvector extension, `documents`, `document_chunks`,
  `ingestion_runs` tables. Runs automatically only on a fresh volume; apply
  manually to an existing volume with
  `docker exec -i customer-compass-db psql -U customer_compass -d customer_compass < db/002-rag.sql`.
- `apps/api/src/rag/chunking.ts` (+ test), `embeddings.ts`, `ingest.ts`,
  `retrieve.ts`.
- `apps/api/src/routes/documents.ts`, `apps/api/src/routes/chat.ts` (extracted
  from `app.ts`, added the `/rag` grounded endpoint).
- `sample-data/documents/*.md` — 8 synthetic documents.
- `apps/web/src/main.tsx`, `apps/web/src/styles.css` — ingestion control, RAG
  toggle, citation rendering.
- `apps/api/package.json` — fixed the `test` script glob (`src/**/*.test.ts`
  silently matched only one directory level without bash `globstar`, so
  `app.test.ts` was never actually running; now wrapped with
  `bash -O globstar`).
