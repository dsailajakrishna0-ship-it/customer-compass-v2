"""Shared chat message type (ported from apps/api/src/llm/types.ts)."""

from typing import Literal, TypedDict


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str
