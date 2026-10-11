"""Calls the OpenRouter cloud model (ported from apps/api/src/llm/cloud.ts,
Stage 4 swappable alternative to Ollama).

OpenRouter exposes an OpenAI-compatible /chat/completions endpoint and
offers several free-tier models (suffixed ":free"). See
https://openrouter.ai/models?max_price=0 for the current free-model list, or
GET /llm/models on this API (backs the web UI's model dropdown).
"""

import os

import httpx

from app.llm.types import ChatMessage

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "liquid/lfm-2.5-2.6b:free")


async def generate_with_cloud(system_prompt: str, messages: list[ChatMessage], model: str | None = None) -> str:
    """`model` is an optional per-request override (from the web UI's "OpenRouter
    model" dropdown); when omitted, falls back to OPENROUTER_MODEL / the
    hardcoded default above."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Add it to apps/api-py/.env to use LLM_PROVIDER=cloud.")

    resolved_model = model or DEFAULT_OPENROUTER_MODEL

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": resolved_model,
                "temperature": 0.3,
                "max_tokens": 350,
                "messages": [{"role": "system", "content": system_prompt}, *messages],
            },
        )
    payload = response.json()

    # OpenRouter can return HTTP 200 with an embedded `error` object when the
    # upstream free-tier provider is overloaded/rate-limited, so we must check
    # for that in addition to a non-2xx status.
    error = payload.get("error")
    if response.status_code != 200 or error:
        detail = (error or {}).get("message") or response.text
        raise RuntimeError(
            f"The cloud model ({resolved_model}) is currently unavailable: {detail or 'unknown error'}. "
            "Free-tier models rotate/rate-limit often - try again shortly or pick a different model "
            "from the dropdown (see apps/api-py/.env.example for how to refresh the free-model list)."
        )

    content = (payload.get("choices") or [{}])[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError("The cloud model returned an empty response. Try again or pick a different model.")
    return content
