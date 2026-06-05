"""CorsMiddleware — adds CORS headers so the Next.js frontend can call the API.

P0 fix (issue 5.1): replaces the broken ``try/except ImportError`` +
``app.add_middleware`` call in :mod:`main` that silently no-oped when
``lauren-middlewares`` was missing.  The middleware is now registered
via the framework's first-class ``global_middlewares=`` kwarg.
"""

from __future__ import annotations

import os

from lauren import middleware
from lauren.types import CallNext, Request, Response

ALLOWED_ORIGINS = frozenset(
    {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    }
)


def _cors_headers(origin: str) -> dict[str, str]:
    allowed = origin if origin in ALLOWED_ORIGINS else ""
    return {
        "access-control-allow-origin": allowed or "*",
        "access-control-allow-methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        "access-control-allow-headers": "Content-Type, Authorization, X-Requested-With",
        "access-control-max-age": "86400",
        "vary": "Origin",
        "access-control-allow-credentials": "true" if allowed else "false",
    }


@middleware()
class CorsMiddleware:
    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        origin = request.headers.get("origin", "") if hasattr(request, "headers") else ""
        if hasattr(request, "method") and request.method == "OPTIONS":
            return Response(b"", status=204).with_headers(_cors_headers(origin))
        response = await call_next(request)
        return response.with_headers(_cors_headers(origin))


def _build_cors_middleware():
    """Return a configured CORS middleware factory (kept for parity with
    the lauren-middlewares ``CORSMiddleware.create()`` pattern).

    Currently unused — :class:`CorsMiddleware` is registered directly
    via ``global_middlewares=`` — but the helper makes it trivial to
    switch to the official factory if the project later installs
    ``lauren-middlewares`` and wants preflight customisation.
    """
    frontend = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    origins = list(ALLOWED_ORIGINS | {frontend})
    return origins
