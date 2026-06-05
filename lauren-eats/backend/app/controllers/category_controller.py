"""Category controller."""

from __future__ import annotations

import logging

from lauren import controller, get

from app.services.menu_service import MenuService

logger = logging.getLogger(__name__)


@controller("/api/categories", tags=["categories"])
class CategoryController:
    def __init__(self, menu_service: MenuService) -> None:
        self._svc = menu_service

    @get("/")
    async def list_categories(self) -> dict:
        categories = await self._svc.list_categories()
        return {"success": True, "data": categories}
