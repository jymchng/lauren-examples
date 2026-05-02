"""Integration tests for the health endpoint.

Uses httpx.AsyncClient + ASGITransport to drive a real LaurenApp.
"""

import json
import os

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

os.environ.setdefault("PAYLOAD_SECRET", "test-secret")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")


@pytest.fixture(scope="module")
def app():
    from app.app_module import AppModule
    from app.interceptors.timing_interceptor import TimingInterceptor
    from app.middlewares.cors_middleware import CorsMiddleware
    from app.middlewares.logging_middleware import LoggingMiddleware
    from lauren import LaurenFactory

    return LaurenFactory.create(
        AppModule,
        global_middlewares=[CorsMiddleware, LoggingMiddleware],
        global_interceptors=[TimingInterceptor],
    )


@pytest_asyncio.fixture()
async def client(app):
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_returns_200(self, client):
        resp = await client.get("/api/health/")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_json(self, client):
        resp = await client.get("/api/health/")
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert data["framework"] == "lauren"

    @pytest.mark.asyncio
    async def test_content_type_json(self, client):
        resp = await client.get("/api/health/")
        assert "application/json" in resp.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_has_x_response_time_from_interceptor(self, client):
        resp = await client.get("/api/health/")
        assert "x-response-time" in resp.headers

    @pytest.mark.asyncio
    async def test_has_cors_headers_from_middleware(self, client):
        resp = await client.get(
            "/api/health/",
            headers={"origin": "http://localhost:3000"},
        )
        assert "access-control-allow-origin" in resp.headers

    @pytest.mark.asyncio
    async def test_cors_preflight(self, client):
        # Global middlewares now run before routing, so CorsMiddleware intercepts
        # OPTIONS and returns 204 even though no OPTIONS route is registered.
        resp = await client.options(
            "/api/health/",
            headers={
                "origin": "http://localhost:3000",
                "access-control-request-method": "GET",
            },
        )
        assert resp.status_code == 204
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
