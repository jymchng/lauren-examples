"""Unit tests for TimingInterceptor."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from lauren import Response
from lauren.types import CallHandler, ExecutionContext, Request
from lauren.types import Headers


def _make_ctx() -> ExecutionContext:
    return ExecutionContext(
        request=Request(method="GET", path="/test"),
        handler_class=None,
        handler_func=None,
        route_template="/test",
    )


def _make_call_handler(result: Any) -> CallHandler:
    async def fn():
        return result

    return CallHandler(fn)


class TestTimingInterceptor:
    @pytest.fixture()
    def interceptor(self):
        from app.interceptors.timing_interceptor import TimingInterceptor

        return TimingInterceptor()

    @pytest.mark.asyncio
    async def test_returns_response_unmodified_except_header(self, interceptor):
        resp = Response.json({"ok": True})
        result = await interceptor.intercept(_make_ctx(), _make_call_handler(resp))
        assert isinstance(result, Response)
        assert result.status == 200

    @pytest.mark.asyncio
    async def test_adds_x_response_time_header(self, interceptor):
        resp = Response.json({"ok": True})
        result = await interceptor.intercept(_make_ctx(), _make_call_handler(resp))
        assert result.headers.get("x-response-time") is not None

    @pytest.mark.asyncio
    async def test_response_time_header_format(self, interceptor):
        resp = Response.json({"ok": True})
        result = await interceptor.intercept(_make_ctx(), _make_call_handler(resp))
        value = result.headers.get("x-response-time")
        assert value is not None
        # Should be like "0ms" or "42ms"
        assert value.endswith("ms")
        assert value[:-2].isdigit()

    @pytest.mark.asyncio
    async def test_non_response_result_returned_as_is(self, interceptor):
        data = {"key": "value"}
        result = await interceptor.intercept(_make_ctx(), _make_call_handler(data))
        assert result is data
        assert "x-response-time" not in result  # not added to dicts

    @pytest.mark.asyncio
    async def test_none_result_returned_as_is(self, interceptor):
        result = await interceptor.intercept(_make_ctx(), _make_call_handler(None))
        assert result is None

    @pytest.mark.asyncio
    async def test_timing_is_non_negative(self, interceptor):
        resp = Response.json({})
        result = await interceptor.intercept(_make_ctx(), _make_call_handler(resp))
        value = result.headers.get("x-response-time")
        ms = int(value[:-2])
        assert ms >= 0

    @pytest.mark.asyncio
    async def test_slow_handler_measured_correctly(self, interceptor):
        async def slow():
            await asyncio.sleep(0.05)
            return Response.json({})

        result = await interceptor.intercept(_make_ctx(), CallHandler(slow))
        value = result.headers.get("x-response-time")
        ms = int(value[:-2])
        assert ms >= 40  # at least ~50ms
