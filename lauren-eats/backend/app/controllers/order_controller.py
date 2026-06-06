"""Order controller.

P0 fixes: same as :mod:`app.controllers.menu_controller` — :class:`Path`
and :class:`Json` extractors, :func:`@exception_handler` class-form
for domain errors.
"""

from __future__ import annotations

import logging

from lauren import (
    Json,
    Path,
    Response,
    Request,
    controller,
    exception_handler,
    get,
    patch,
    post,
    use_exception_handlers,
)
from lauren import exception_handler

from app.models.order import CreateOrderRequest, UpdateOrderRequest
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)


class OrderNotFound(LookupError):
    """Raised when an order id does not exist."""


@exception_handler(OrderNotFound)
class OrderNotFoundHandler:
    async def catch(self, exc: OrderNotFound, request: Request) -> Response:
        logger.info("order: %s not found", exc)
        return Response.json(
            {"success": False, "error": f"Order {exc.args[0]!r} not found."},
            status=404,
        )


@controller("/api/orders", tags=["orders"])
@use_exception_handlers(OrderNotFoundHandler)
class OrderController:
    def __init__(self, order_service: OrderService) -> None:
        self._svc = order_service

    @get("/")
    async def list_orders(
        self,
        status: str = "",
        userId: str = "",
    ) -> dict:
        orders = await self._svc.list_orders(
            status=status or None,
            user_id=userId or None,
        )
        return {"success": True, "data": orders}

    @post("/")
    async def create_order(self, body: Json[CreateOrderRequest]) -> dict:
        order = await self._svc.create_order(
            body.model_dump(exclude_unset=True, by_alias=True)
        )
        return {"success": True, "data": order}, 201

    @get("/{id}")
    async def get_order(self, id: str = Path()) -> dict:
        order = await self._svc.get_order(id)
        if order is None:
            raise OrderNotFound(id)
        return {"success": True, "data": order}

    @patch("/{id}")
    async def update_order(
        self,
        id: str = Path(),
        body: Json[UpdateOrderRequest] = ...,
    ) -> dict:
        order = await self._svc.update_order_status(id, body.status)
        if order is None:
            raise OrderNotFound(id)
        return {"success": True, "data": order}
