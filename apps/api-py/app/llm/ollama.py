"""Calls the local Ollama chat model (ported from apps/api/src/llm/ollama.ts,
Stage 2 behavior, unchanged)."""

import os

import httpx

from app.llm.types import ChatMessage

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11435")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")


async def generate_with_ollama(system_prompt: str, messages: list[ChatMessage]) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "messages": [{"role": "system", "content": system_prompt}, *messages],
                "options": {"temperature": 0.3, "num_predict": 350},
            },
        )
    if response.status_code != 200:
        raise RuntimeError("The local model is not ready. Start Ollama and pull the configured model.")
    payload = response.json()
    return payload.get("message", {}).get("content") or "I could not generate a response."
