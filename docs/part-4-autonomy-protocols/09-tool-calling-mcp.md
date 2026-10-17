# Stage 9 — Tool calling via MCP

**Part:** IV — Autonomy & Protocols
**Status:** Planned

## Goal

Let the LLM request constrained application operations through validated tool
schemas instead of attempting to invent or directly execute actions — implemented
using the **Model Context Protocol (MCP)**, the emerging standard for exposing
tools to LLMs, rather than a one-off custom tool-schema format.

## Why MCP

- MCP standardizes how tools are described, discovered, and invoked, so the
  same CRM/RAG tool server could later be reused by other MCP-compatible
  clients/agents, not just this app's chat loop.
- It is the same protocol pattern used by modern coding/AI assistants, making
  this a directly transferable, current skill rather than a bespoke exercise.

## Candidate tools (exposed as an MCP server)

- Customer lookup/search
- Deal and interaction lookup
- Knowledge search (Stage 3/5 RAG retrieval)
- Support-case lookup
- Email drafting
- Follow-up task creation

## Design rules

Read operations can be performed after authorization. Mutating operations such
as task creation require schema validation, access checks, error handling, audit
logging, and user confirmation before execution.

## Acceptance criteria

For a request such as "show the current deal and summarize recent discussions,"
the model selects database and retrieval tools through the MCP server. For
"create a follow-up task," it presents a proposed action and waits for
confirmation.

## How to run the app

```bash
cd /home/devarapallim/Murali/git-personal/customer-compass
docker compose up -d db ollama
npm install
npm run dev
```

The MCP tool server runs as part of the API process (or as a sibling process
started by `npm run dev`, depending on final implementation).

## How to test manually

1. **Read-tool selection**
   Ask "Show me the current deal for Acme and summarize recent discussions"
   and confirm the model's response indicates it used a deal-lookup tool and a
   knowledge-search tool (visible in logs/trace or an "actions used" UI panel).
2. **Mutating tool requires confirmation**
   Ask "Create a follow-up task to call Acme next week" and confirm the
   assistant proposes the task and explicitly waits for your confirmation
   before it is created — it must not create it automatically.
3. **Confirm and verify the action**
   Approve the proposed task and confirm it now appears in the CRM (e.g. via
   `GET /api/companies/:id` or a tasks endpoint).
4. **Unauthorized tool use blocked**
   As a user without permission for a given company, ask for that company's
   deal details and confirm the tool call is rejected rather than silently
   returning data.
5. **Audit trail**
   Confirm every tool invocation (read and mutating) produced an audit log
   entry (building on Stage 7).

## Developer note

Expected files/modules for this increment:

- `apps/api/src/mcp/server.ts` — MCP server exposing the CRM/RAG tools.
- `apps/api/src/mcp/tools/customer.ts`, `deal.ts`, `knowledge.ts`, `task.ts` —
  independently validated tool implementations, each with an MCP tool schema.
- `apps/api/src/mcp/dispatcher.ts` — authorization, validation, and safe
  execution boundary shared by all tools.
- `apps/api/src/chat/tool-loop.ts` — model/tool orchestration using the MCP
  client to call the tool server.
- `db/migrations/...` — task table and tool/audit records if not introduced
  earlier.
- `apps/web/src/...` — proposed-action review and explicit confirmation UI.

Tool functions must call existing CRM/RAG modules; they must not duplicate SQL or
retrieval logic in the model orchestration layer.
