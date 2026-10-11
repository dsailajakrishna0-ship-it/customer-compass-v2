"""FastAPI service for the v2 stack migration (Stage 6 prep, PR 3 of N).

This service runs alongside the existing Express API (apps/api) during the
migration. PR 2 proved the FastAPI + uv + Docker wiring works end to end
(health check against Postgres). PR 3 adds the first real feature: document
ingestion into Qdrant (see app/rag/, app/routes/documents.py). Chat/RAG query
routes are still served by the Express API until a later PR ports them too.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db import close_pool, get_pool
from app.rag.qdrant_store import close_client
from app.routes.documents import router as documents_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_pool()
    await close_client()


app = FastAPI(title="Customer Compass API (Python)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Mirrors apps/api's GET /health: confirms the API process is up *and*
    can reach Postgres, not just that the process is alive."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001 - surfaced as a clear 503 below
        raise HTTPException(status_code=503, detail=f"Database unreachable: {exc}") from exc
    return {"status": "ok"}
