# Stage 10 — Agentic CRM assistant

**Part:** IV — Autonomy & Protocols
**Status:** Planned

## Goal

Use a bounded multi-step workflow only where it creates real value: analyze an
account, retrieve supporting evidence, recommend a next action, and optionally
create a confirmed task.

## Intended flow

```text
Identify customer -> fetch CRM facts -> retrieve history -> reason -> recommend
-> ask for confirmation -> execute task tool -> audit result
```

## Design rules

- Keep simple factual questions as direct SQL or direct RAG, not agent loops.
- Prefer deterministic workflows when the action sequence is known.
- Bound tool count, time, and retries; surface intermediate evidence to users.
- Never let an agent autonomously perform important external actions without
  explicit confirmation.

## Acceptance criteria

The agent produces an evidence-backed follow-up recommendation and only creates
a task after explicit user approval. Its execution trace is inspectable.

## How to run the app

```bash
cd /home/devarapallim/Murali/git-personal/customer-compass-v2
docker compose up -d db qdrant ollama api-py
cd apps/web && npm run dev
```

## How to test manually

1. **Trigger the agentic workflow**
   Ask "Analyze Acme Fabrication's account and recommend a next action" and
   confirm the assistant walks through: fetching CRM facts, retrieving history,
   then producing a reasoned recommendation with supporting evidence.
2. **Inspect the execution trace**
   Confirm there is a visible/inspectable trace (UI panel or log) showing each
   step taken (which tools were called, in what order, with what evidence).
3. **Confirmation gate before action**
   Confirm the agent stops and asks for explicit approval before creating any
   follow-up task, and does not create it if you decline.
4. **Bounded execution**
   Confirm the agent does not loop indefinitely — it should stop after a
   documented maximum number of tool calls/steps even on an ambiguous request.
5. **Simple questions bypass the agent**
   Ask a simple factual question (e.g. "What is Acme's industry?") and confirm
   it is answered directly via SQL/RAG, not routed through the full agentic
   workflow.

## Developer note

Expected files/modules for this increment:

- `apps/api-py/app/agent/workflow.py` — bounded orchestration state machine.
- `apps/api-py/app/agent/planner.py` — optional planning/reasoning adapter with
  strict time/tool limits.
- `apps/api-py/app/agent/trace.py` — inspectable evidence and tool execution trace.
- `apps/api-py/app/agent/policies.py` — confirmation and stop conditions.
- `apps/api-py/app/mcp/` — the existing Stage 9 MCP tools; no parallel action mechanism.
- `apps/web/src/...` — workflow status, evidence, recommendation, and
  confirmation experience.
- `docs/agent-boundaries.md` — decision table for direct RAG, tools,
  deterministic workflows, and agentic flows.

The agent is a composition layer over proven Stage 5 and Stage 9 capabilities;
it must not become a second implementation of retrieval, authorization, or task
creation.
