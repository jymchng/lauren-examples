"""Pydantic schemas for the team feature."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TeamRequest(BaseModel):
    task: str = Field(..., min_length=1)
    conversation_id: str | None = None


class TeamEventData(BaseModel):
    """Typed payload for SSE events emitted by the team endpoint."""

    event: str
    data: Any
