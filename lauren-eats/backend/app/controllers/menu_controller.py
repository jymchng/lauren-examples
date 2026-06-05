"""Menu controller — menu items and categories endpoints.

P0 fixes:
- Query parameters are auto-detected from scalar type annotations
  (issue 4.8).  The framework's :func:`_is_implicit_query_type`
  promotes any ``int | str | bool | float`` parameter to a query param
  when no other marker is supplied.
- Path parameters use :class:`Path` (issue 4.8).
- PATCH body is parsed via :class:`Json` (issue 4.7) — the orphan
  Pydantic models in :mod:`app.models.menu` are now used.
- Domain errors are translated to 4xx/5xx by :func:`@exception_handler`
  (issue 5.1).
"""

from __future__ import annotations

import logging

from lauren import (
    Json,
    Path,
    Request,
    Response,
    controller,
    exception_handler,
    get,
    patch,
    use_exception_handlers,
)

from app.models.menu import MenuItemUpdate
from app.services.menu_service import MenuService

logger = logging.getLogger(__name__)


class MenuItemNotFound(LookupError):
    """Raised when a menu item id does not exist."""


@exception_handler(MenuItemNotFound)
class MenuItemNotFoundHandler:
    async def catch(self, exc: MenuItemNotFound, request: Request) -> Response:
        logger.info("menu: %s not found", exc)
        return Response.json(
            {"success": False, "error": f"Menu item {exc.args[0]!r} not found."},
            status=404,
        )


@controller("/api/menu", tags=["menu"])
@use_exception_handlers(MenuItemNotFoundHandler)
class MenuController:
    def __init__(self, menu_service: MenuService) -> None:
        self._svc = menu_service

    @get("/")
    async def list_menu(
        self,
        page: int = 1,
        limit: int = 12,
        category: str = "all",
        search: str = "",
        isVegetarian: bool = False,
        isVegan: bool = False,
        isGlutenFree: bool = False,
        spicyLevel: int = 0,
        isPopular: bool = False,
    ) -> dict:
        result = await self._svc.list_menu_items(
            page=page,
            limit=min(100, max(1, limit)),
            category=category,
            search=search or None,
            is_vegetarian=isVegetarian,
            is_vegan=isVegan,
            is_gluten_free=isGlutenFree,
            spicy_level=spicyLevel,
            is_popular=isPopular,
        )
        return {"success": True, "data": result["data"], "pagination": result["pagination"]}

    @get("/{id}")
    async def get_menu_item(self, id: str = Path()) -> dict:
        item = await self._svc.get_menu_item(id)
        if item is None:
            raise MenuItemNotFound(id)
        return {"success": True, "data": item}

    @patch("/{id}")
    async def update_menu_item(
        self,
        id: str = Path(),
        body: Json[MenuItemUpdate] = ...,
    ) -> dict:
        payload = body.model_dump(exclude_unset=True)
        item = await self._svc.update_menu_item(id, payload)
        if item is None:
            raise MenuItemNotFound(id)
        return {"success": True, "data": item}
