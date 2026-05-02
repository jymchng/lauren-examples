"""CorsMiddleware — adds CORS headers so the Next.js frontend can call the API.

Registered globally in ``main.py`` so it applies to every request.

The middleware handles preflight (OPTIONS) requests inline without forwarding
them to the router, and appends CORS headers to all other responses
(including ``EventStream`` SSE responses — ``with_headers`` preserves the
stream reference).
"""

from lauren import middleware
from lauren.types import CallNext, Request, Response

ALLOWED_ORIGINS = frozenset(
    {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }
)


def _cors_headers(origin: str) -> dict[str, str]:
    allowed = origin if origin in ALLOWED_ORIGINS else ""
    return {
        "access-control-allow-origin": allowed or "*",
        "access-control-allow-methods": "GET, POST, OPTIONS",
        "access-control-allow-headers": "Content-Type, X-Signature",
        "access-control-max-age": "86400",
        "vary": "Origin",
    }


@middleware()
class CorsMiddleware:
    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        origin = request.headers.get("origin", "")

        # Preflight — respond immediately without hitting the router
        if request.method == "OPTIONS":
            return Response(b"", status=204).with_headers(_cors_headers(origin))

        response = await call_next(request)
        return response.with_headers(_cors_headers(origin))
