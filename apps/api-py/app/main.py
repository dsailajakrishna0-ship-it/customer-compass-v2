"""FastAPI skeleton for the v2 stack migration (Stage 6 prep, PR 2 of N).

This service runs alongside the existing Express API (apps/api) during the
migration — it does not yet serve any of the real chat/RAG/CRM routes. Its
only job right now is to prove the FastAPI + uv + Docker wiring works end to
end, including a real Postgres connectivity check, before ingestion and
retrieval logic are ported over in later PRs.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db import close_pool, get_pool


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_pool()


app = FastAPI(title="Customer Compass API (Python)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
