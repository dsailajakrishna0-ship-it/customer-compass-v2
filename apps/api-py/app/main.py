"""FastAPI service for the v2 stack migration (Stage 6 prep, PR 4 of N).

This service runs alongside the existing Express API (apps/api) during the
migration. PR 2 proved the FastAPI + uv + Docker wiring works end to end
(health check against Postgres). PR 3 added document ingestion into Qdrant.
PR 4 adds the chat/RAG query routes (general chat, grounded RAG, CRM
copilot) and the OpenRouter model list — the full feature set the Express
API's frontend-facing routes provide. The frontend is not switched over to
this service yet (that's PR 5).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db import close_pool, get_pool
from app.rag.qdrant_store import close_client
from app.routes.chat import router as chat_router
from app.routes.documents import router as documents_router
from app.routes.llm import router as llm_router


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
app.include_router(chat_router)
app.include_router(llm_router)


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
