"""Reservation controller."""

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
    post,
    use_exception_handlers,
)

from app.models.reservation import CreateReservationRequest, UpdateReservationRequest
from app.services.reservation_service import ReservationService

logger = logging.getLogger(__name__)


class ReservationNotFound(LookupError):
    """Raised when a reservation id does not exist."""


@exception_handler(ReservationNotFound)
class ReservationNotFoundHandler:
    async def catch(self, exc: ReservationNotFound, request: Request) -> Response:
        logger.info("reservation: %s not found", exc)
        return Response.json(
            {"success": False, "error": f"Reservation {exc.args[0]!r} not found."},
            status=404,
        )


@controller("/api/reservations", tags=["reservations"])
@use_exception_handlers(ReservationNotFoundHandler)
class ReservationController:
    def __init__(self, reservation_service: ReservationService) -> None:
        self._svc = reservation_service

    @get("/")
    async def list_reservations(
        self,
        date: str = "",
        status: str = "",
    ) -> dict:
        reservations = await self._svc.list_reservations(
            date=date or None,
            status=status or None,
        )
        return {"success": True, "data": reservations}

    @post("/")
    async def create_reservation(self, body: Json[CreateReservationRequest]) -> dict:
        reservation = await self._svc.create_reservation(body.model_dump(exclude_unset=True, by_alias=True))
        return {"success": True, "data": reservation}, 201

    @patch("/{id}")
    async def update_reservation(
        self,
        id: str = Path(),
        body: Json[UpdateReservationRequest] = ...,
    ) -> dict:
        reservation = await self._svc.update_reservation_status(id, body.status)
        if reservation is None:
            raise ReservationNotFound(id)
        return {"success": True, "data": reservation}

    @get("/{id}")
    async def get_reservation(self, id: str = Path()) -> dict:
        reservation = await self._svc.get_reservation(id)
        if reservation is None:
            raise ReservationNotFound(id)
        return {"success": True, "data": reservation}
