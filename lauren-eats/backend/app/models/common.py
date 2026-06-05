"""Common Pydantic models shared across the application."""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: str | None = None
    message: str | None = None


class Pagination(BaseModel):
    page: int = 1
    limit: int = 12
    total: int = 0
    total_pages: int = Field(default=0, alias="totalPages")
    has_more: bool = Field(default=False, alias="hasMore")

    class Config:
        populate_by_name = True


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T] = []
    pagination: Pagination
