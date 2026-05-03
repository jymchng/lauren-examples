"""Pydantic schemas for the chat feature."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1)
    model: str = "openai/gpt-4o-mini"
    conversation_id: str | None = None
    # Banking demo: authenticated user injected by the server-signed payload.
    # Defaults to "alice" so the general /api/agent/ endpoint still works.
    user_id: str = "alice"


class ChatResponse(BaseModel):
    """Used only in OpenAPI docs — the actual endpoint streams SSE."""

    content: str
