"""Query-time retrieval: embed the question, find the closest chunks, and
shape them into citable sources for the LLM prompt and the UI.

Ported from apps/api/src/rag/retrieve.ts. Searches Qdrant instead of
Postgres/pgvector — each chunk's payload is already fully self-contained
(document title, source path, doc type, company name/id, content, char
offsets), so no join back to Postgres is needed here.
"""

from dataclasses import dataclass

from qdrant_client.models import FieldCondition, Filter, IsNullCondition, MatchValue, PayloadField

from app.rag.embeddings import embed_text
from app.rag.qdrant_store import COLLECTION_NAME, get_client

# Retrieval: embed the question, then ask Qdrant for the top-k most similar chunks
DEFAULT_TOP_K = 4
# Chunks below this cosine similarity are treated as not relevant enough to cite.
#
# Tuned empirically for gemini-embedding-001 (see evals/README.md, Stage 6):
# sampled questions against the live sample-data corpus showed genuinely
# relevant chunks scoring ~0.50-0.80, while clearly unrelated questions
# ("What is the capital of France?", "How do I bake a chocolate cake?")
# scored ~0.42-0.44. 0.45 sits in the gap between those two clusters. Note
# this does NOT fully solve plausible-but-uncovered questions (e.g. "What
# is our refund policy?" scores ~0.50-0.54, same range as real matches,
# because it's topically CRM/support-adjacent) — that's a known limitation
# of similarity-only filtering; the LLM's "not in the sources" response
# text is still the real safety net for those, and the eval suite checks
# for that behavior rather than expecting zero citations.
MIN_SIMILARITY = 0.45


@dataclass
class RetrievedChunk:
    chunk_id: int | str
    document_id: int
    document_title: str
    source_path: str
    doc_type: str
    company_name: str | None
    chunk_index: int
    content: str
    similarity: float


def _company_filter(company_id: int | None) -> Filter | None:
    if company_id is None:
        return None
    # Another customer's material is never retrieved for a scoped question:
    # only this company's documents and company-agnostic documents (e.g.
    # product overviews, company_id IS NULL) are eligible.
    return Filter(
        should=[
            FieldCondition(key="company_id", match=MatchValue(value=company_id)),
            IsNullCondition(is_null=PayloadField(key="company_id")),
        ]
    )


async def retrieve_relevant_chunks(
    question: str,
    company_id: int | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """Finds the closest document chunks to `question`. When `company_id` is
    given (company-scoped question), only that company's documents and
    company-agnostic documents are eligible."""
    query_embedding = await embed_text(question)
    client = get_client()

    results = await client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        query_filter=_company_filter(company_id),
        limit=top_k,
        with_payload=True,
    )

    return [
        RetrievedChunk(
            chunk_id=point.id,
            document_id=point.payload["document_id"],
            document_title=point.payload["document_title"],
            source_path=point.payload["source_path"],
            doc_type=point.payload["doc_type"],
            company_name=point.payload.get("company_name"),
            chunk_index=point.payload["chunk_index"],
            content=point.payload["content"],
            similarity=point.score,
        )
        for point in results.points
        if point.score >= MIN_SIMILARITY
    ]


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Builds the numbered, citable context block injected into the LLM prompt."""
    return "\n\n".join(
        f"[{i + 1}] Source: {chunk.document_title} ({chunk.doc_type})\n{chunk.content}"
        for i, chunk in enumerate(chunks)
    )
