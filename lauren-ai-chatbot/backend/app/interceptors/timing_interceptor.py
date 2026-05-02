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

from pydantic import BaseModel

from lauren import interceptor
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
        if isinstance(result, BaseModel):
            # Auto-serialize Pydantic models so the header can be attached.
            # Lauren will use this Response directly without double-serializing.
            return Response.json(result.model_dump()).with_header("x-response-time", header_value)
        return result
