"""TimingInterceptor — measures handler execution time and annotates the response.

Unlike middleware, interceptors receive the full ``ExecutionContext`` so they
know which controller + route they are wrapping.  The interceptor adds an
``X-Response-Time`` header to every response — including ``EventStream``
responses, because ``Response.with_header`` preserves the underlying stream.

Registered globally in ``main.py`` via ``global_interceptors=[TimingInterceptor]``.

Example response header::

    X-Response-Time: 42ms
"""

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
        # For msgspec.Struct, dataclass, or any other serializable value:
        # convert to Response using the active encoder so the header can be attached.
        if result is not None and not isinstance(result, (dict, list, str, int, float, bool)):
            return Response.json(result, encoder=get_active_encoder()).with_header("x-response-time", header_value)
        return result
