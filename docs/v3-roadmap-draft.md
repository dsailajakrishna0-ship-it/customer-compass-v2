# Customer Compass V3 — Roadmap Draft (2026-10-19)

> Planning note only — not yet committed to any repo. Move into
> `docs/` of the new `customer-compass-v3` repo once that repo exists.

## Why a new repo, not a branch

`customer-compass-v2` is being kept as a **clean, linear, closed
learning artifact**: each stage (1 through 9, currently) was hand-built
to understand the underlying mechanics (RAG, CRM routing, guardrails,
cloud/local LLM providers, MCP tool calling) before reaching for a
framework. Bolting new product features and framework-comparison
exercises onto it would blur that focus and make it harder to point
back to as "here's what stage N looked like."

`customer-compass-v3` starts fresh, seeded from v2's final state,
once v2 is considered "done" (Stage 9 merged, docs-only audit PR
landed, any further core stages complete). V3's learning goal shifts
from *"build the fundamentals by hand"* to *"how do frameworks/tools
accelerate or change this, and what else can the product do."*

## Two tracks within V3

Kept separate because they have different goals — shipping working
features vs. learning by side-by-side comparison — even though they
may touch the same code areas.

### Track A — Product features
Extends what the app can actually do for a user.

- **add-new-company-ui** — UI form + `POST /api/companies` to create
  companies/contacts/deals from the browser (currently seed-only).
- **multi-format-doc-ingestion** — PDF (`pypdf`/`pdfplumber`), Word
  (`python-docx`), Excel/CSV (`openpyxl`/`pandas`) support in the
  ingestion pipeline, alongside the current Markdown-only path.
  Tabular data (sheets) likely routed through the structured
  CRM/tool-calling path rather than vector search.
- **rag-adaptive-scaling** — explore adaptive top-k (confidence/
  query-length based) instead of the current fixed `top_k=4`; note
  infra-level autoscaling as likely out of scope for a learning repo.

### Track B — Framework exploration
Reimplements existing hand-rolled pieces using well-known frameworks,
purely to compare control/transparency vs. speed/ecosystem — not to
replace the hand-rolled version permanently.

- **LangChain core** — `OllamaEmbeddings`/`GoogleGenerativeAIEmbeddings`
  + `QdrantVectorStore` + `retriever.invoke()` vs. our
  `embeddings.py`/`retrieve.py`; `ChatOllama`/`ChatOpenAI` vs. our
  provider-swap logic in `app/llm`; `ChatPromptTemplate` vs. manual
  f-string prompts; `bind_tools()`/`create_tool_calling_agent()` vs.
  our hand-rolled Stage 9 MCP fenced-text protocol.
- **LangGraph** — stateful multi-step agent graphs, applied to the
  RAG-vs-CRM routing logic and any future multi-step agent work.
- **LangSmith** — hosted tracing/evals, compared against our current
  `logger.info(...)` lines + the `tool_audit_log` Postgres table.
- **Other frameworks for RAG specifically** (most mature/competitive
  space) — LlamaIndex, Haystack, as alternatives to LangChain for the
  retrieval piece.

## Explicitly NOT in V3

- **docs-only-audit-pr** — stays in v2. It's about restricting v2's
  *own* docs to their actual completed-stage content, so it belongs
  to v2's closing housekeeping, not v3's new work.

## Future domain expansion considerations (possibly a separate repo, not V3)

V3 (above) extends the **existing small CRM domain** with more
features and framework comparisons. Separately, there's an open
question of outgrowing the CRM domain itself to practice agentic AI
at a scope closer to what AI/IT services companies are actually
staffing for. Raised by user on 2026-10-19: "agentic AI... limited
scope with our small CRM domain... what our AI IT companies demand."

Candidate domains considered, ranked by market-demand fit:

1. **IT Service Management / Helpdesk Agentic AI** (ServiceNow/ITSM
   style) — ticket triage, KB search, applying known fixes, escalation
   with context, resolution verification. High current demand across
   IT services companies (TCS/Infosys/Accenture/Wipro-type GenAI
   practices). Natural extension of the Stage 9 MCP tool-calling
   pattern at larger scale (more tools, more entities).
2. **DevOps/SRE Incident-Response Copilot** — reads alerts/logs/
   metrics, correlates root cause across services, runs runbooks,
   proposes/executes remediation with human-in-loop approval. Strong
   enterprise demand; fits the existing "propose -> confirm -> execute"
   pattern from Stage 9 well.
3. **Claims/Underwriting Processing Agent (Insurance/Finance, BFSI)**
   — document-heavy (reuses RAG skills directly), multi-step
   verification, fraud flags, policy lookups. High demand in
   BFSI-focused IT services, but more regulatory/compliance modeling
   overhead to do realistically.
4. **Contact-center/Customer Support Agentic AI at enterprise scale**
   — closest to the current CRM domain, but broader: multi-channel
   (chat/email/voice transcripts) and multiple backend systems
   (billing, order mgmt, refunds), not just CRM facts.

Recommendation (if/when picked up): **#1 (IT Service Desk) or #2 (SRE
Incident Response)** — both are squarely what IT services companies
build GenAI practices around, and both naturally extend the existing
tool-calling/guardrail/audit-log architecture to more tools, more
entities, and genuinely multi-step autonomous workflows.

This is explicitly **not scoped into V3** — V3 stays CRM-domain,
extending features/frameworks on top of it. A new domain this
different in shape (different entities, different tool surface,
different compliance/approval semantics) would warrant its own
separate repo if/when it's picked up, likely informed by whatever
was learned building out V3 first.

## Suggested sequencing

1. Finish v2: merge PR #11 (Stage 9), complete any further planned
   core stages, land the docs-only audit PR.
2. Create `customer-compass-v3` repo, seeded from v2's final `main`.
3. Track A and Track B can proceed in parallel within v3, but keep
   their PRs/branches separate so each stays reviewable on its own
   terms (feature work vs. framework-comparison write-ups).
4. Revisit this draft once v3 actually kicks off — refine scope based
   on whatever changed in v2 by then.
