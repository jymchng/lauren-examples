"""Redirect controller — resolves short codes and issues 302 redirects."""

from __future__ import annotations

import logging

from lauren import (
    Path,
    Request,
    Response,
    controller,
    exception_handler,
    get,
    use_exception_handlers,
)

from app.services.url_service import UrlExpired, UrlNotFound, UrlService

logger = logging.getLogger(__name__)


@exception_handler(UrlNotFound)
class RedirectNotFoundHandler:
    async def catch(self, exc: UrlNotFound, request: Request) -> Response:
        return Response.json({"error": f"Short code {exc.args[0]!r} not found."}, status=404)


@exception_handler(UrlExpired)
class RedirectExpiredHandler:
    async def catch(self, exc: UrlExpired, request: Request) -> Response:
        return Response.json({"error": f"Short URL {exc.args[0]!r} has expired."}, status=410)


@controller("/api/r", tags=["redirect"])
@use_exception_handlers(RedirectNotFoundHandler, RedirectExpiredHandler)
class RedirectController:
    def __init__(self, svc: UrlService) -> None:
        self._svc = svc

    @get("/{code}")
    async def redirect(self, code: str = Path(), request: Request = ...) -> Response:
        ip = request.client.host if request.client else ""
        ua = request.headers.get("user-agent", "")
        ref = request.headers.get("referer", "")
        target = await self._svc.record_redirect(code, ip=ip, user_agent=ua, referer=ref)
        return Response.redirect(target, status=302)
