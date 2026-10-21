# Architecture overview

This is the "how all the pieces fit together" map for customer-compass-v2.
For the per-stage build history, see [tech-stack.md](tech-stack.md) and the
`part-*/` stage documents. For the frontend's internal layering, see
[fe/fe-architecture-overview.md](fe/fe-architecture-overview.md).

## System diagram

```
┌─────────────────────────────┐
│   apps/web (React + Vite)   │   http://localhost:5173
│   dashboard + chat UI       │
└──────────────┬──────────────┘
               │ fetch() — JSON over HTTP
               ▼
┌─────────────────────────────────────────────────────────────┐
│           apps/api-py (FastAPI, Python, uv)                 │   http://localhost:8001
│                                                               │
│  /health             — DB connectivity check                 │
│  /api/v1/companies*  — company list/detail (Postgres)        │
│  /api/v1/documents*  — ingest pipeline + inspection           │
│  /api/v1/chat*       — general / RAG / CRM copilot chat       │
│  /api/v1/llm/models  — OpenRouter free/paid model catalog     │
│                                                               │
│  app/db.py        — Postgres connection pool (asyncpg)        │
│  app/rag/         — chunking, embeddings, Qdrant client        │
│  app/chat/router.py — keyword-based RAG-vs-CRM query router   │
│  app/crm/queries.py — structured CRM fact lookups              │
│  app/llm/         — provider.py (dispatch+fallback), cloud.py,│
│                      ollama.py, types.py (GenerationResult)    │
└───────┬───────────────────┬───────────────────┬───────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌─────────────────────┐
│   Postgres      │   │    Qdrant      │   │  Ollama (local)      │
│ (pgvector image,│   │ (vector store  │   │  or OpenRouter        │
│  relational data│   │  for document  │   │  (cloud, OpenAI-     │
│  only in v2:    │   │  chunk         │   │  compatible API)      │
│  companies,     │   │  embeddings)   │   │                       │
│  deals, contacts,│  │                │   │  Chosen per-request   │
│  interactions,  │   │                │   │  via `provider` field,│
│  ingestion_runs)│   │                │   │  with automatic       │
└───────────────┘   └───────────────┘   │  fallback (Stage 7)   │
                                          └─────────────────────┘
```

## Stage-by-stage: what's new at each layer

Same idea as the Stage 9 vs. Stage 10 comparison table, extended across
every stage. **Bold** = introduced at that stage; everything else in a row
is reused unchanged from an earlier stage. Read top to bottom to see the
architecture diagram above build up incrementally. Full prose write-up per
stage: [tech-stack.md](tech-stack.md).

| Stage | New component(s) | New capability unlocked | Builds on |
| --- | --- | --- | --- |
| **1 — CRM Foundation** | **PostgreSQL** (companies, contacts, deals, interactions) | Structured CRM data exists at all; no LLM/AI yet | — |
| **2 — First LLM Chat** | **Ollama** (local, `qwen2.5:3b`), `/api/v1/chat` | First chat/completion endpoint; no CRM data access yet | Stage 1 DB (unused by chat so far) |
| **3 — Basic RAG** | **Ollama embeddings** (`mxbai-embed-large`), **`pgvector`** (same Postgres DB), `/api/v1/chat/rag` | Answers grounded in retrieved, cited document chunks instead of the model's own knowledge | Stage 1 DB, Stage 2 chat model |
| **4 — Cloud LLM Provider** | **OpenRouter** (cloud, free tier), `GET /api/v1/llm/models`, Model/provider dropdowns in UI | Live, per-request choice between local and cloud inference — Ollama still works unchanged | Stage 2 chat plumbing |
| **5 — Realistic CRM RAG** | **Query router** (`chat/router.py`), **`crm/queries.py`**, `/api/v1/chat/crm`, 3-way chat-mode selector | Questions routed to structured SQL facts, document retrieval, or both — and the UI visibly separates "verified facts" from "cited claims" | Stage 1 DB, Stage 3 retrieval |
| **6 — Retrieval Evaluation** | **promptfoo** eval suite (`evals/`), LLM-as-judge rubric | Retrieval/grounding correctness and refusal behavior are now measurable, not just manually eyeballed — used to empirically tune `MIN_SIMILARITY` | Stage 3 retrieval, Stage 5 CRM routing |
| **7 — Production Concerns** | **Cross-provider auto-fallback**, **per-request `usage` telemetry** | A failing provider no longer surfaces a hard error — it silently retries on the other provider and *tells you it did* (fallback flag + cost/latency footer in UI) | Stage 4 dual providers |
| **8 — Prompt-Injection Guardrails** | **Rule-based input/document guard**, `<untrusted_context>` delimiting, `guardrail` field on every response | Injection attempts (direct or planted in a document) are neutralized in place and surfaced visibly, instead of silently succeeding or blocking the whole request | Stage 3 document ingestion, Stage 5 CRM chat, Stage 7 visibility pattern |
| **9 — Tool Calling (MCP)** | **MCP server/client** (`app/mcp/`), fenced-text tool-call protocol, `/api/v1/chat/tools`, **`tasks`**/**`tool_audit_log`** tables | Model can call live tools **mid-conversation** (read CRM/docs, propose+confirm a mutating action) instead of everything being stuffed into the prompt upfront | Stage 1 DB, Stage 3 retrieval, Stage 5 CRM queries, Stage 8 guardrail (applied to tool results too) |
| **10 — Agentic Assistant** | *(planned, not yet designed)* — likely a **planning loop**, **multi-step orchestration loop**, self-feedback/checking, broader approval surface | Model pursues a **multi-step goal** autonomously (e.g. "follow up with every stalled deal this week"), not just one reactive tool call per turn | Stage 9 tools, Stage 8 guardrails |

## Why two databases

Postgres and Qdrant have different jobs and neither replaces the other here:

- **Postgres** (`pgvector/pgvector:pg17` image, but pgvector's vector type
  itself is unused in v2 — see note below) holds all relational/structured
  CRM data: companies, contacts, deals, interactions, and ingestion run
  history. This is what `/api/v1/companies*` and the CRM-facts half of
  `/api/v1/chat/crm` read from.
- **Qdrant** holds document chunk embeddings for retrieval. v1 used
  pgvector's vector column directly in Postgres; v2 migrated to a dedicated
  vector database (Stage migration documented in `docs/tech-stack.md`) to
  learn a real vector-DB's API (collections, payload filtering by
  `company_id` for CRM-mode scoping, similarity search) rather than treating
  vector search as "just another SQL column."

## Why two LLM providers

- **Ollama** — local, free, private, but limited by local hardware (runs
  `qwen2.5:3b`, a small model — hence terser/odd-citation-placement answers
  observed during testing).
- **OpenRouter (cloud)** — swappable, can offer much larger models even on
  the free tier, but subject to internet access, external rate limits, and
  the usual cloud-provider instability.

Both are always wired up side by side (`app/llm/provider.py`); a request
can choose either via `provider`, and since Stage 7, a failure in the
requested provider triggers one automatic retry with the other before the
request fails outright (see "Stage 7" below).

## Request flow: one chat question, start to finish (RAG mode example)

1. User types a question in `ChatInput` (apps/web); `useChat.ts` POSTs to
   `/api/v1/chat/rag` with the message history, `provider`, and optional
   `model`.
2. `app/routes/chat.py::rag_chat` calls `retrieve_relevant_chunks()`
   (`app/rag/retrieve.py`), which embeds the question (same embedding model
   used at ingest time) and queries Qdrant for the nearest chunks above a
   similarity threshold.
3. If no chunks clear the threshold, a canned "nothing relevant found"
   response is returned immediately — no LLM call, no false citations.
4. Otherwise, the retrieved chunks are formatted into a numbered context
   block (`build_context()`) and appended to the message history under a
   system prompt that requires every claim to carry a `[n]` citation.
5. `app/llm/provider.py::generate()` dispatches to the requested provider
   (`cloud.py` or `ollama.py`), timing the call and extracting token usage
   from the provider's response. On failure, it retries once with the other
   provider (Stage 7) before giving up.
6. The route returns `{ message, citations, provider, usage }` — `usage`
   is the Stage 7 telemetry object (tokens, latency, cost, fallback flag).
7. The frontend renders the answer, a citation list, a provider tag, and
   (Stage 7) a small usage footer under the message
   (`MessageBubble.tsx`).

CRM mode (`/api/v1/chat/crm`) adds one more fork before step 4: a
keyword-based classifier (`app/chat/router.py`) decides whether the
question wants structured CRM facts, document retrieval, or both, and
whichever company is named gets its retrieval scoped to that
`company_id` in Qdrant (payload filter) so citations never leak across
companies.

## Stage 7: provider fallback + telemetry

Added in PR #8 (`feature/stage-7-production-concerns`). Full design
rationale and testing steps live in
[part-3-trust-safety/07-production-concerns.md](part-3-trust-safety/07-production-concerns.md).
In short: `generate()` now returns a `GenerationResult` (content + actual
provider/model used + token counts + latency + estimated cost), and
automatically retries the other provider once if the first one raises,
flagging the response so a provider outage is visible instead of silent.

## Local dev vs. Docker networking

Two different hostnames point at the same Ollama container depending on
who's asking:

- From **your host machine** (e.g. a manual `curl` or browser): `localhost:11435`
  (the port Docker Compose maps to the container).
- From **inside the `api-py` container** (i.e. what `OLLAMA_URL` is actually
  set to in `docker-compose.yml`): `http://ollama:11434` — the
  compose-network-internal DNS name and the container's native port.

The same pattern applies to `QDRANT_URL` (`http://qdrant:6333` from inside
the network) and `DATABASE_URL` (`db:5432` from inside the network).

## Where to look for more detail

| Topic | Where |
| --- | --- |
| Full stage-by-stage build history | [tech-stack.md](tech-stack.md) |
| API endpoints, request/response shapes | [api-reference.md](api-reference.md) |
| Frontend component/hook layering | [fe/fe-architecture-overview.md](fe/fe-architecture-overview.md) |
| Frontend chat request lifecycle | [fe/fe-chat-request-flow.md](fe/fe-chat-request-flow.md) |
| Retrieval evaluation (promptfoo) suite | [../evals/README.md](../evals/README.md) |
| Local startup troubleshooting | [v2-startup-troubleshooting.md](v2-startup-troubleshooting.md) |
