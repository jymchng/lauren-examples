"""LoggingMiddleware — logs every inbound request and outbound response.

Registered globally in ``main.py`` so it wraps all routes, including the
SSE chat endpoint.  For SSE responses the status code is logged when the
response object is returned (before the stream body is consumed), which is
the earliest reliable log point.
"""

import logging
import time

from lauren import middleware
from lauren.types import CallNext, Request, Response

logger = logging.getLogger("lauren_chatbot")


@middleware()
class LoggingMiddleware:
    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        start = time.perf_counter()
        logger.info("→ %s %s", request.method, request.path)
        try:
            response = await call_next(request)
            elapsed_ms = int((time.perf_counter() - start) * 1_000)
            logger.info(
                "← %s %s  status=%d  [%dms]",
                request.method,
                request.path,
                response.status,
                elapsed_ms,
            )
            return response
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1_000)
            logger.error(
                "✗ %s %s  error=%r  [%dms]",
                request.method,
                request.path,
                exc,
                elapsed_ms,
            )
            raise
