"""Seed controller — database seeding endpoint."""

from __future__ import annotations

import logging

from lauren import (
    Request,
    Response,
    controller,
    exception_handler,
    post,
    use_exception_handlers,
)

from app.db.database import DatabaseService
from app.db.seed import run_seed

logger = logging.getLogger(__name__)


class SeedFailed(RuntimeError):
    """Raised when seeding fails for any reason."""


@exception_handler(SeedFailed)
class SeedFailedHandler:
    async def catch(self, exc: SeedFailed, request: Request) -> Response:
        logger.error("seed: %s", exc)
        return Response.json(
            {"success": False, "error": f"Seeding failed: {exc}"},
            status=500,
        )


@controller("/api/seed", tags=["seed"])
@use_exception_handlers(SeedFailedHandler)
class SeedController:
    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    @post("/")
    async def seed(self) -> dict:
        try:
            result = await run_seed(self._db)
            return {"success": True, "data": result}
        except Exception as exc:
            raise SeedFailed(str(exc)) from exc
