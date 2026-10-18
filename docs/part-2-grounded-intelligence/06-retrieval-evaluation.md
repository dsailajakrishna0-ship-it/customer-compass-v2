# Stage 6 — Retrieval quality and evaluation

**Part:** II — Grounded Intelligence
**Status:** Planned

## Goal

Improve retrieval deliberately and measure it with a repeatable evaluation set
rather than relying on a few successful chat examples.

## Planned work

- Build an approximately 30-question benchmark with expected source documents.
- Add hybrid keyword + semantic retrieval where it improves results.
- Evaluate reranking, query rewriting, and multi-query retrieval only when their
  measured benefit justifies added complexity.
- Record retrieval relevance/precision/recall, answer correctness, groundedness,
  citation correctness, latency, and token consumption.
- Add an **LLM-as-judge** scorer (e.g. via RAGAS, DeepEval, or a small custom
  rubric prompt) to automatically rate groundedness and answer correctness
  against expected sources, reducing reliance on manual eyeballing.
- Compare local-model (Ollama) vs. cloud-model (Stage 4) retrieval-answer
  quality and latency on the same benchmark.

## Acceptance criteria

The repository contains an executable evaluation workflow and a baseline results
report that makes regressions visible, including an LLM-judge score alongside
deterministic retrieval metrics.

## How to run the app

```bash
cd /home/devarapallim/Murali/git-personal/customer-compass
docker compose up -d db ollama
npm install
npm run dev
```

The evaluation workflow runs separately from the app (see below) and talks to
the running API.

## How to test manually

1. **Run the benchmark**
   ```bash
   npx tsx scripts/run-evals.ts
   ```
   Confirm it processes all ~30 questions against the running API without
   crashing, and writes a timestamped result file under `evals/results/`.
2. **Inspect the report**
   ```bash
   npx tsx scripts/report-evals.ts evals/results/<latest-file>.json
   ```
   Confirm the report shows retrieval precision/recall, groundedness, citation
   correctness, latency, and an LLM-judge score per question.
3. **Spot-check the LLM-judge score against your own judgment**
   Pick 3–5 questions, read the retrieved sources and answer yourself, and
   confirm your manual verdict (correct/incorrect, grounded/ungrounded)
   roughly matches the automated judge score.
4. **Regression check**
   Intentionally break something small (e.g. lower the similarity threshold in
   `retrieve.ts`), re-run the benchmark, and confirm the report visibly shows a
   metric regression rather than silently passing.
5. **Compare providers**
   Re-run the benchmark once with `LLM_PROVIDER=ollama` and once with
   `LLM_PROVIDER=cloud` (Stage 4) and compare the two reports side by side.

## Developer note

Expected files/modules for this increment:

- `evals/questions.json` — approximately 30 versioned test questions, expected
  sources, and expected answer properties.
- `apps/api/src/rag/hybrid-search.ts` and `rerank.ts` — retrieval improvements,
  introduced only when evaluated.
- `apps/api/src/eval/llm-judge.ts` — LLM-as-judge scoring adapter (groundedness,
  correctness) usable with either configured LLM provider.
- `scripts/run-evals.ts` — repeatable benchmark runner.
- `scripts/report-evals.ts` — metrics aggregation and report generation.
- `evals/results/` — timestamped, reviewable baseline outputs (excluding secrets).
- `docs/evaluation-results.md` — interpretation of metrics and trade-offs.

Do not replace the baseline retriever wholesale; preserve it as a comparison
point for each proposed quality improvement.
