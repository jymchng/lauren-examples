"""Unit tests for CORS and Logging middlewares.

Tests the middleware logic in isolation using a mock call_next callable.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from lauren import Request, Response
from lauren.types import Headers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(
    method: str = "GET",
    path: str = "/",
    headers: dict | None = None,
) -> Request:
    raw = [(k.lower(), v) for k, v in (headers or {}).items()]
    return Request(method=method, path=path, headers=Headers(raw))


def _ok_response() -> Response:
    return Response.json({"ok": True})


async def _call_next(request: Request) -> Response:
    return _ok_response()


# ---------------------------------------------------------------------------
# CorsMiddleware
# ---------------------------------------------------------------------------

class TestCorsMiddleware:
    @pytest.fixture()
    def mw(self):
        from app.middlewares.cors_middleware import CorsMiddleware
        return CorsMiddleware()

    @pytest.mark.asyncio
    async def test_options_returns_204(self, mw):
        req = _make_request(method="OPTIONS", path="/api/chat/", headers={"origin": "http://localhost:3000"})
        resp = await mw.dispatch(req, _call_next)
        assert resp.status == 204

    @pytest.mark.asyncio
    async def test_options_has_cors_headers(self, mw):
        req = _make_request(method="OPTIONS", headers={"origin": "http://localhost:3000"})
        resp = await mw.dispatch(req, _call_next)
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    @pytest.mark.asyncio
    async def test_options_does_not_call_next(self, mw):
        called = []
        async def next_fn(r):
            called.append(True)
            return _ok_response()
        req = _make_request(method="OPTIONS", headers={"origin": "http://localhost:3000"})
        await mw.dispatch(req, next_fn)
        assert not called

    @pytest.mark.asyncio
    async def test_get_adds_cors_headers(self, mw):
        req = _make_request(method="GET", headers={"origin": "http://localhost:3000"})
        resp = await mw.dispatch(req, _call_next)
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    @pytest.mark.asyncio
    async def test_unknown_origin_falls_back_to_wildcard(self, mw):
        req = _make_request(method="GET", headers={"origin": "http://evil.com"})
        resp = await mw.dispatch(req, _call_next)
        # Falls back to wildcard when origin not in allowlist
        assert resp.headers.get("access-control-allow-origin") == "*"

    @pytest.mark.asyncio
    async def test_no_origin_header(self, mw):
        req = _make_request(method="GET")
        resp = await mw.dispatch(req, _call_next)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_allowed_methods_header(self, mw):
        req = _make_request(method="OPTIONS", headers={"origin": "http://localhost:3000"})
        resp = await mw.dispatch(req, _call_next)
        assert resp.headers.get("access-control-allow-methods") is not None

    @pytest.mark.asyncio
    async def test_x_signature_in_allowed_headers(self, mw):
        req = _make_request(method="OPTIONS", headers={"origin": "http://localhost:3000"})
        resp = await mw.dispatch(req, _call_next)
        allowed = resp.headers.get("access-control-allow-headers") or ""
        assert "X-Signature" in allowed

    @pytest.mark.asyncio
    async def test_post_calls_next_and_adds_headers(self, mw):
        req = _make_request(method="POST", headers={"origin": "http://127.0.0.1:3000"})
        resp = await mw.dispatch(req, _call_next)
        assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"


# ---------------------------------------------------------------------------
# LoggingMiddleware
# ---------------------------------------------------------------------------

class TestLoggingMiddleware:
    @pytest.fixture()
    def mw(self):
        from app.middlewares.logging_middleware import LoggingMiddleware
        return LoggingMiddleware()

    @pytest.mark.asyncio
    async def test_passes_through_response(self, mw):
        req = _make_request()
        resp = await mw.dispatch(req, _call_next)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_logs_method_and_path(self, mw):
        import logging
        req = _make_request(method="POST", path="/api/chat/")
        with patch("app.middlewares.logging_middleware.logger") as mock_log:
            await mw.dispatch(req, _call_next)
            calls = [str(c) for c in mock_log.info.call_args_list]
            assert any("POST" in c for c in calls)
            assert any("/api/chat/" in c for c in calls)

    @pytest.mark.asyncio
    async def test_logs_response_status(self, mw):
        req = _make_request()
        with patch("app.middlewares.logging_middleware.logger") as mock_log:
            await mw.dispatch(req, _call_next)
            all_calls = "".join(str(c) for c in mock_log.info.call_args_list)
            assert "200" in all_calls

    @pytest.mark.asyncio
    async def test_logs_error_and_reraises(self, mw):
        async def failing_next(r):
            raise ValueError("boom")
        req = _make_request()
        with patch("app.middlewares.logging_middleware.logger") as mock_log:
            with pytest.raises(ValueError, match="boom"):
                await mw.dispatch(req, failing_next)
            mock_log.error.assert_called_once()
