"""Pydantic models for order-related requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateOrderItemRequest(BaseModel):
    menu_item_id: str = Field(..., alias="menuItemId")
    quantity: int = 1
    notes: str | None = None

    class Config:
        populate_by_name = True


class CreateOrderRequest(BaseModel):
    user_id: str | None = Field(None, alias="userId")
    items: list[CreateOrderItemRequest]
    type: str = "dine_in"  # dine_in, takeout, delivery
    notes: str | None = None
    table_number: str | None = Field(None, alias="tableNumber")

    class Config:
        populate_by_name = True


class UpdateOrderRequest(BaseModel):
    status: str  # pending, confirmed, preparing, ready, delivered, cancelled


class OrderItemOut(BaseModel):
    id: str
    order_id: str = Field("", alias="orderId")
    menu_item_id: str = Field("", alias="menuItemId")
    quantity: int = 1
    unit_price: float = Field(0, alias="unitPrice")
    total_price: float = Field(0, alias="totalPrice")
    notes: str | None = None
    created_at: str = Field("", alias="createdAt")
    menu_item: dict | None = Field(None, alias="menuItem")

    class Config:
        populate_by_name = True
