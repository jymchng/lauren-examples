"""Pydantic models for reservation-related requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateReservationRequest(BaseModel):
    customer_name: str = Field(..., alias="customerName")
    customer_phone: str = Field(..., alias="customerPhone")
    customer_email: str | None = Field(None, alias="customerEmail")
    party_size: int = Field(..., alias="partySize")
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    special_requests: str | None = Field(None, alias="specialRequests")
    occasion: str | None = None  # birthday, anniversary, business, casual
    user_id: str | None = Field(None, alias="userId")

    class Config:
        populate_by_name = True


class UpdateReservationRequest(BaseModel):
    status: str  # pending, confirmed, cancelled, completed
