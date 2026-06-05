"""Pydantic models for chat-related requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SendChatMessageRequest(BaseModel):
    message: str
    conversation_id: str | None = Field(None, alias="conversationId")
    agent_type: str | None = Field(None, alias="agentType")
    context: dict | None = None

    class Config:
        populate_by_name = True
