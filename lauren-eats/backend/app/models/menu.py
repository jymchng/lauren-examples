"""Pydantic models for menu-related requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CategoryOut(BaseModel):
    id: str
    name: str
    name_zh: str | None = Field(None, alias="nameZh")
    slug: str
    description: str | None = None
    icon: str | None = None
    sort_order: int = Field(0, alias="sortOrder")
    is_active: bool = Field(True, alias="isActive")
    created_at: str = Field("", alias="createdAt")
    updated_at: str = Field("", alias="updatedAt")
    menu_items: list[dict] | None = Field(None, alias="menuItems")

    class Config:
        populate_by_name = True


class MenuItemOut(BaseModel):
    id: str
    name: str
    name_zh: str | None = Field(None, alias="nameZh")
    description: str
    price: float
    image: str | None = None
    category_id: str = Field("", alias="categoryId")
    spicy_level: int = Field(0, alias="spicyLevel")
    is_vegetarian: bool = Field(False, alias="isVegetarian")
    is_vegan: bool = Field(False, alias="isVegan")
    is_gluten_free: bool = Field(False, alias="isGlutenFree")
    is_popular: bool = Field(False, alias="isPopular")
    is_available: bool = Field(True, alias="isAvailable")
    calories: int | None = None
    preparation_time: int | None = Field(None, alias="preparationTime")
    ingredients: str | None = None
    allergens: str | None = None
    tags: str | None = None
    created_at: str = Field("", alias="createdAt")
    updated_at: str = Field("", alias="updatedAt")
    category: dict | None = None

    class Config:
        populate_by_name = True


class MenuItemUpdate(BaseModel):
    is_available: bool | None = Field(None, alias="isAvailable")
    is_popular: bool | None = Field(None, alias="isPopular")
    price: float | None = None
    name: str | None = None
    description: str | None = None

    class Config:
        populate_by_name = True
