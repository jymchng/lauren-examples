"""URL management endpoints — CRUD for shortened URLs."""

from __future__ import annotations

import logging

from lauren import (
    Json,
    Path,
    Request,
    Response,
    controller,
    delete,
    exception_handler,
    get,
    patch,
    post,
    use_exception_handlers,
)

from app.models.url import CreateUrlRequest, UpdateUrlRequest
from app.services.url_service import UrlCodeConflict, UrlNotFound, UrlService

logger = logging.getLogger(__name__)


@exception_handler(UrlNotFound)
class UrlNotFoundHandler:
    async def catch(self, exc: UrlNotFound, request: Request) -> Response:
        return Response.json({"success": False, "error": f"URL {exc.args[0]!r} not found."}, status=404)


@exception_handler(UrlCodeConflict)
class UrlCodeConflictHandler:
    async def catch(self, exc: UrlCodeConflict, request: Request) -> Response:
        return Response.json({"success": False, "error": str(exc)}, status=409)


@controller("/api/urls", tags=["urls"])
@use_exception_handlers(UrlNotFoundHandler, UrlCodeConflictHandler)
class UrlController:
    def __init__(self, svc: UrlService) -> None:
        self._svc = svc

    @post("/")
    async def create_url(self, body: Json[CreateUrlRequest]) -> dict:
        record = await self._svc.create(body)
        return {"success": True, "data": record.__dict__}

    @get("/")
    async def list_urls(
        self,
        page: int = 1,
        limit: int = 20,
        search: str = "",
    ) -> dict:
        result = await self._svc.list_urls(page=page, limit=limit, search=search)
        return {"success": True, **result}

    @get("/{code}/stats")
    async def get_url_stats(self, code: str = Path()) -> dict:
        stats = await self._svc.get_stats(code)
        return {"success": True, "data": stats}

    @get("/{code}")
    async def get_url(self, code: str = Path()) -> dict:
        record = await self._svc.get_by_code(code)
        return {"success": True, "data": record.__dict__}

    @patch("/{code}")
    async def update_url(self, code: str = Path(), body: Json[UpdateUrlRequest] = ...) -> dict:
        record = await self._svc.update(code, body)
        return {"success": True, "data": record.__dict__}

    @delete("/{code}")
    async def delete_url(self, code: str = Path()) -> dict:
        await self._svc.delete(code)
        return {"success": True}
