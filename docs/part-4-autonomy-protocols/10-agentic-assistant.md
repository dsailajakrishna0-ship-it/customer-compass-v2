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

## Use case and agents

**Use case: Account Follow-up Recommender.** The user names a company; the
system gathers evidence, recommends a next action, has it reviewed, drafts a
follow-up task, and creates it only after the user confirms.

Stage 10 uses **3 agents** (an agent here = an LLM that makes a decision from
evidence; it does not choose the order of steps). **Orchestration is plain
code**, not an LLM.

| # | Agent | Decision it makes | Reads | Writes |
| --- | --- | --- | --- | --- |
| 1 | **Analyst agent** | Which next action to recommend, and why | CRM facts, deals, interactions, retrieved documents | Nothing |
| 2 | **Reviewer agent** | Is the recommendation supported by the evidence? Approve, or send back with reasons | Analyst output + same evidence | Nothing |
| 3 | **Task Drafter agent** | The follow-up task note for the user to confirm | Approved recommendation | Nothing (the task is created by the Stage 9 tool after confirmation) |

Not agents, deliberately: gathering CRM facts and retrieving history are
deterministic steps that call the existing Stage 5 and Stage 9 tools. They
make no decisions, so labelling them agents would be misleading. V3 turns
them into real agents (see `docs/v3-roadmap-draft.md`).

```text
Gather evidence (code) -> Analyst agent -> Reviewer agent
   -> (sent back? Analyst agent revises, at most once)
   -> Task Drafter agent -> user confirms -> create task (Stage 9 tool) -> audit
```

Concepts this covers: agent roles, handoffs between agents, a bounded
feedback loop (review and revise), human approval, and an inspectable trace.
What it does not cover: agents choosing their own tools, agents working in
parallel, memory across sessions, or a real multi-agent framework.

## Design rules

- Keep simple factual questions as direct SQL or direct RAG, not agent loops.
- Prefer deterministic workflows when the action sequence is known.
- Bound tool count, time, and retries; surface intermediate evidence to users.
- Never let an agent autonomously perform important external actions without
  explicit confirmation.
- Bounds (env vars, starting values): at most 6 steps and 60 seconds per run,
  and one Analyst revision round so the Analyst and Reviewer cannot loop.
- Retrieved text and the user's message still pass the Stage 8 guardrails
  before any agent sees them.

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
   step taken (which tools were called, in what order, with what evidence),
   and the output and verdict of the Analyst agent, Reviewer agent and Task
   Drafter agent.
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
- `apps/api-py/app/agent/agents.py` — the Analyst agent, Reviewer agent and
  Task Drafter agent (one prompt and one structured output each).
- `apps/api-py/app/agent/trace.py` — inspectable evidence and tool execution trace.
- `apps/api-py/app/agent/policies.py` — confirmation and stop conditions.
- `apps/api-py/app/mcp/` — the existing Stage 9 MCP tools (MCP: a protocol that exposes tools to the model); no parallel action mechanism.
- `apps/web/src/...` — workflow status, evidence, recommendation, and
  confirmation experience.
- `docs/agent-boundaries.md` — decision table for direct RAG, tools,
  deterministic workflows, and agentic flows.

The agent is a composition layer over proven Stage 5 and Stage 9 capabilities;
it must not become a second implementation of retrieval, authorization, or task
creation.
