# Testing guide — run it, open it, click it, ask it

One stop for: the commands to start everything, the URLs to watch while you
work, every dropdown combination in the chat UI, and sample questions to
test each one (with what you should expect back). For architecture/API
details, see [architecture.md](architecture.md) and
[api-reference.md](api-reference.md) instead — this doc is for actually
clicking around and testing.

## 1. Commands to start everything

```bash
cd /home/devarapallim/Murali/git-personal/customer-compass-v2

# Backend stack: Postgres, Qdrant, Ollama, the FastAPI service
docker-compose up -d db qdrant ollama api-py

# First time only (or after a DB/Ollama volume reset): pull the local model
docker exec customer-compass-v2-ollama ollama pull qwen2.5:3b

# Frontend dev server
cd apps/web && npm run dev
```

If you rebuilt backend code (anything under `apps/api-py/app/`), rebuild the
container instead of relying on a stale image:
```bash
docker-compose up -d --build api-py
```

Frontend code changes hot-reload automatically — no restart needed while
`npm run dev` is running.

**One-time setup per fresh environment**: in the UI, click **Ingest
documents** (top-left of the dashboard) once, so RAG/CRM modes have
something to retrieve. You only need to repeat this if the database or
Qdrant volume gets reset.

## 2. URLs to open and monitor

| URL | What it's for |
| --- | --- |
| `http://localhost:5173` | The web app itself. |
| `http://localhost:8001/health` | Backend health check — confirms the API is up and can reach Postgres. |
| `http://localhost:8001/docs` | Live interactive Swagger UI for every API endpoint — good for poking at the API directly without the frontend. |
| `http://localhost:6333/dashboard` | Qdrant's built-in web UI — inspect the `document_chunks` collection, point counts, payloads. |
| `docker-compose logs -f api-py` | Backend request/error logs, including the `llm_usage` line (Stage 7 telemetry) logged on every chat answer. |
| `docker ps --format "{{.Names}}\t{{.Status}}"` | Confirms all 4 containers (`db`, `qdrant`, `ollama`, `api-py`) are actually `Up`, not silently stuck in `Created`. |

## 3. The dropdowns, and what each combination means

The chat panel (`http://localhost:5173` → **Chat** nav link) has up to
three controls:

1. **Chat mode**: `General` / `Document knowledge (RAG)` / `CRM copilot`
2. **Provider**: `Local (Ollama)` / `Cloud (OpenRouter)`
3. **Model** (only shown when Provider = Cloud): any free OpenRouter model
   from the dropdown — paid models are listed but disabled/greyed out.

There's **no company selector** — name the company in your question text
and the app scopes retrieval to it automatically. Seeded companies:
**Acme Fabrication** (customer), **Northstar Logistics** (lead), **Harbor &
Pine** (customer).

### Combo 1 — General × Local/Cloud

Plain LLM chat, no CRM data at all, regardless of provider. Use this to
sanity-check "is the model itself reachable" independent of retrieval.

| Ask | Expect |
| --- | --- |
| *"What's the capital of France?"* | A normal general-knowledge answer, no citations, no CRM facts. |
| *"What deals does Acme Fabrication have open?"* | The model should say it has no CRM data access — **not** a made-up answer. |

### Combo 2 — Document knowledge (RAG) × Local/Cloud

Grounded only in ingested documents, with required `[n]` citations. Not
company-scoped by default — citations can span companies unless your
question names one.

| Ask | Expect |
| --- | --- |
| *"What did Acme Fabrication say about the volume discount?"* | Cites `acme-email-discount.md` (Ravi Patel's request), similarity ~0.6-0.8. |
| *"Does the Fleet Visibility package include alerting, and can alerts be set per customer?"* | Cites `product-fleet-visibility.md` + Northstar's alerting documents; answer should be complete, not cut off mid-sentence (Stage 6.1 fix, PR #7). |
| *"What's your refund policy?"* | No ingested document covers this — expect either zero citations with a canned "could not find" message, or (if the threshold is borderline) citations present but the model explicitly declining to answer rather than guessing — both are correct, documented behavior. |
| *"What's the capital of France?"* | Zero citations — nothing in the document set is relevant (similarity-threshold fix from Stage 6). |

### Combo 3 — CRM copilot × Local/Cloud

Routes the question to structured DB facts, document retrieval, or both,
and scopes retrieval to the named company. The most "real assistant" mode.

| Ask | Expect |
| --- | --- |
| *"What open deals does Acme Fabrication have?"* | Facts only — "Premium Operations Plan renewal", $48,000, open, expected close 2026-10-15. No citation markers on this part. |
| *"What did Acme Fabrication say about onboarding in their emails?"* | Citations only — Acme's own interactions (volume discount email, renewal call, support ticket), not Northstar's or Harbor & Pine's. |
| *"What's the status of Acme's renewal deal, and what have we discussed with them recently?"* | **Both** — facts (the renewal deal) and citations (Acme's interactions), clearly separated in the answer. |
| *"What has Northstar Logistics discussed about alerting limits?"* | Citations only, scoped to Northstar — confirms a second company's scoping also works (not just Acme). |
| *"What open deals does Acme Fabrication have, based on Northstar's documents?"* (adversarial/ambiguous phrasing) | Scoping check — confirms citations never leak Northstar's documents into an Acme-named question, even when phrased to try to confuse the router. |
| *"What open deals does a company we've never heard of have?"* | Neither facts nor citations found — canned "could not find a matching company or deal" message, no hallucinated company. |

### Provider/model notes (apply to every combo above)

- **Local (Ollama · qwen2.5:3b)**: fully offline, no API key, slower on
  CPU, occasionally places citation markers oddly (e.g. `"[1], [3] The
  answer is..."` instead of inline) — a stylistic quirk of the small model,
  not a bug.
- **Cloud (OpenRouter, free tier)**: pick any model from the dropdown.
  Free models occasionally rate-limit — as of Stage 7 this now **auto-retries
  via Local (Ollama)** instead of failing, and the answer will show an
  orange "⚠ Cloud was unavailable — answered via Local instead" note when
  that happens. Every answer (either provider) now shows a small usage
  footer: model name, latency, tokens, estimated cost ($0 today — every
  model offered is free-tier).

### UI mechanics worth re-confirming after recent fixes

- The **model dropdown** (long, grouped free/paid list) should open and
  stay open — click any option anywhere in the list, including near the
  bottom; click-outside and Escape should both close it (Stage 6.1 fix,
  custom `ModelPicker` component, PR #7).
- The **chat mode** and **provider** dropdowns (short, 2-3 options each)
  should also work normally — these were fixed earlier and aren't expected
  to regress.
- Forcing an error (e.g. an invalid model id, or a genuine rate-limit)
  should show the *real* error/fallback message in the chat, never a
  generic "Something went wrong." (Stage 6.1 / Stage 7 fix).

## 4. Quick backend-only checks (skip the UI entirely)

Useful when you want to isolate "is this a backend bug or a UI bug":

```bash
# Health
curl -s http://localhost:8001/health

# RAG, cloud provider
curl -s -X POST http://localhost:8001/api/v1/chat/rag \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What did Acme Fabrication say about the volume discount?"}],"provider":"cloud"}' \
  | python3 -m json.tool

# CRM copilot, local provider
curl -s -X POST http://localhost:8001/api/v1/chat/crm \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What open deals does Acme Fabrication have?"}],"provider":"ollama"}' \
  | python3 -m json.tool

# Force a fallback (Stage 7) — an invalid cloud model fails over to Ollama
curl -s -X POST http://localhost:8001/api/v1/chat/rag \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Does the Fleet Visibility package include alerting?"}],"provider":"cloud","model":"not-a-real-model"}' \
  | python3 -m json.tool
```

**Expect** (verified 2026-10-17): HTTP 200, a real cited answer (not an
error), and:
```json
"provider": "ollama",
"usage": {
  "provider": "ollama",
  "model": "qwen2.5:3b",
  "fallbackUsed": true,
  "fallbackFrom": "cloud"
}
```
`provider` at the top level flips to `"ollama"` (the provider that actually
answered), even though the request asked for `"cloud"` — this is the
auto-retry in action, not a bug.

## 5. Related docs

| Doc | For |
| --- | --- |
| [architecture.md](architecture.md) | System diagram, why two databases/providers, full request-flow walkthrough. |
| [api-reference.md](api-reference.md) | Every endpoint's exact request/response shape. |
| [tech-stack.md](tech-stack.md) | Per-stage build history and the active technology per capability. |
| [v2-startup-troubleshooting.md](v2-startup-troubleshooting.md) | Known local-startup quirks (container-name clashes, shared ports, env-file setup) and their fixes. |
| [part-2-grounded-intelligence/06-retrieval-evaluation.md](part-2-grounded-intelligence/06-retrieval-evaluation.md) + [../evals/README.md](../evals/README.md) | The automated promptfoo eval suite, if you want to run these same kinds of checks without manual clicking. |
| [part-3-trust-safety/07-production-concerns.md](part-3-trust-safety/07-production-concerns.md) | Stage 7 fallback/telemetry design + its own manual test steps. |
