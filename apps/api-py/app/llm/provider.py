"""Dispatches generation to the configured LLM backend (ported from
apps/api/src/llm/provider.ts).

Both backends are always available side by side; nothing is replaced.
`provider` is an explicit per-request choice (e.g. from a UI selector); when
omitted it falls back to LLM_PROVIDER (defaults to "ollama" — unchanged
Stage 2 behavior). `model` is only used by the "cloud" backend, letting the
caller pick a specific OpenRouter model (see GET /llm/models); when omitted
it falls back to OPENROUTER_MODEL.
"""

import os
from typing import Literal, get_args

from app.llm.cloud import generate_with_cloud
from app.llm.ollama import generate_with_ollama
from app.llm.types import ChatMessage

LlmProvider = Literal["ollama", "cloud"]

DEFAULT_LLM_PROVIDER: LlmProvider = os.environ.get("LLM_PROVIDER", "ollama")  # type: ignore[assignment]
if DEFAULT_LLM_PROVIDER not in get_args(LlmProvider):
    DEFAULT_LLM_PROVIDER = "ollama"


async def generate(
    system_prompt: str,
    messages: list[ChatMessage],
    provider: LlmProvider | None = None,
    model: str | None = None,
) -> str:
    resolved = provider or DEFAULT_LLM_PROVIDER
    if resolved == "cloud":
        return await generate_with_cloud(system_prompt, messages, model)
    if resolved == "ollama":
        return await generate_with_ollama(system_prompt, messages)
    raise ValueError(f'Unknown LLM provider "{resolved}". Use "ollama" or "cloud".')
