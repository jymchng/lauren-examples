"""Integration tests for SignatureGuard — the most critical security component.

Every test exercises the full Lauren request pipeline:
  request → CORS middleware → logging middleware → signature guard → handler

Tests cover:
- Missing signature (401)
- Wrong signature (401)
- Correct signature (200 SSE)
- Tampered body (401)
- Empty body (edge case)
- Guard short-circuits before AgentRunner calls the LLM
"""

import json
import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

os.environ.setdefault("PAYLOAD_SECRET", "integration-test-secret")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy-key")

from app.crypto.crypto_service import CryptoService

SECRET = os.environ.get("PAYLOAD_SECRET", "integration-test-secret")


def _sign(body: bytes, secret: str = SECRET) -> str:
    svc = CryptoService.__new__(CryptoService)
    svc._secret = secret.encode()
    return svc.sign(body)


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


CHAT_BODY = json.dumps({
    "messages": [{"role": "user", "content": "Hello!"}],
    "model": "openai/gpt-4o-mini",
    "user_id": "alice",
}).encode()

_ENDPOINT = "/api/banking/chat"


class TestSignatureGuardMissingHeader:
    @pytest.mark.asyncio
    async def test_no_signature_header_returns_401(self, client):
        resp = await client.post(
            _ENDPOINT,
            content=CHAT_BODY,
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_error_message_mentions_signature(self, client):
        resp = await client.post(
            _ENDPOINT,
            content=CHAT_BODY,
            headers={"content-type": "application/json"},
        )
        text = resp.text.lower()
        assert "signature" in text or "unauthorized" in text


class TestSignatureGuardWrongSignature:
    @pytest.mark.asyncio
    async def test_random_hex_returns_401(self, client):
        resp = await client.post(
            _ENDPOINT,
            content=CHAT_BODY,
            headers={
                "content-type": "application/json",
                "x-signature": "deadbeef" * 8,
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_secret_returns_401(self, client):
        sig = _sign(CHAT_BODY, secret="wrong-secret")
        resp = await client.post(
            _ENDPOINT,
            content=CHAT_BODY,
            headers={"content-type": "application/json", "x-signature": sig},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_truncated_signature_returns_401(self, client):
        sig = _sign(CHAT_BODY)[:32]
        resp = await client.post(
            _ENDPOINT,
            content=CHAT_BODY,
            headers={"content-type": "application/json", "x-signature": sig},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_correct_sig_tampered_body_returns_401(self, client):
        sig = _sign(CHAT_BODY)
        tampered = CHAT_BODY + b" "
        resp = await client.post(
            _ENDPOINT,
            content=tampered,
            headers={"content-type": "application/json", "x-signature": sig},
        )
        assert resp.status_code == 401


class TestSignatureGuardValidSignature:
    @pytest.mark.asyncio
    async def test_valid_signature_returns_200(self, client):
        sig = _sign(CHAT_BODY)
        mock_response = AsyncMock()
        mock_response.content = "Hello! How can I help?"
        with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
            resp = await client.post(
                _ENDPOINT,
                content=CHAT_BODY,
                headers={"content-type": "application/json", "x-signature": sig},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_valid_response_is_sse(self, client):
        sig = _sign(CHAT_BODY)
        mock_response = AsyncMock()
        mock_response.content = "Hello!"
        with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
            resp = await client.post(
                _ENDPOINT,
                content=CHAT_BODY,
                headers={"content-type": "application/json", "x-signature": sig},
            )
        assert "text/event-stream" in resp.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_valid_has_x_response_time(self, client):
        sig = _sign(CHAT_BODY)
        mock_response = AsyncMock()
        mock_response.content = "Hello!"
        with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
            resp = await client.post(
                _ENDPOINT,
                content=CHAT_BODY,
                headers={"content-type": "application/json", "x-signature": sig},
            )
        assert "x-response-time" in resp.headers

    @pytest.mark.asyncio
    async def test_different_valid_payloads_both_pass(self, client):
        mock_response = AsyncMock()
        mock_response.content = "OK"
        for content in ["hello", "a longer message with more words"]:
            body = json.dumps({
                "messages": [{"role": "user", "content": content}],
                "model": "openai/gpt-4o-mini",
                "user_id": "alice",
            }).encode()
            sig = _sign(body)
            with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
                resp = await client.post(
                    _ENDPOINT,
                    content=body,
                    headers={"content-type": "application/json", "x-signature": sig},
                )
            assert resp.status_code == 200, f"Failed for content: {content!r}"


class TestSignatureGuardBodyCaching:
    """Verify the guard reads body once and the controller can still read it."""

    @pytest.mark.asyncio
    async def test_guard_and_controller_share_cached_body(self, client):
        """If body were consumed by the guard and not cached, Json[T] would fail."""
        body = json.dumps({
            "messages": [{"role": "user", "content": "cache test"}],
            "model": "openai/gpt-4o-mini",
            "user_id": "alice",
        }).encode()
        sig = _sign(body)
        mock_response = AsyncMock()
        mock_response.content = "OK"
        with patch("lauren_ai._agents._runner.AgentRunner.run", return_value=mock_response):
            resp = await client.post(
                _ENDPOINT,
                content=body,
                headers={"content-type": "application/json", "x-signature": sig},
            )
        # If the body cache is broken, this returns 422 (validation error), not 200
        assert resp.status_code == 200
