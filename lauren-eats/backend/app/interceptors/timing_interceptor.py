"""TimingInterceptor — adds ``X-Response-Time`` header to every response.

P0 fix (issue 7.3): the backend was missing an interceptor that times
handler execution.  Without it there is no per-request telemetry.
"""

from __future__ import annotations

import time
from typing import Any

from lauren import interceptor
from lauren.serialization import get_active_encoder
from lauren.types import CallHandler, ExecutionContext, Response


@interceptor()
class TimingInterceptor:
    async def intercept(self, ctx: ExecutionContext, call_handler: CallHandler) -> Any:
        start = time.perf_counter()
        result = await call_handler.handle()
        elapsed_ms = int((time.perf_counter() - start) * 1_000)
        header_value = f"{elapsed_ms}ms"

        if isinstance(result, Response):
            return result.with_header("x-response-time", header_value)
        if result is not None and not isinstance(result, (dict, list, str, int, float, bool)):
            return Response.json(result, encoder=get_active_encoder()).with_header(
                "x-response-time", header_value
            )
        return result
