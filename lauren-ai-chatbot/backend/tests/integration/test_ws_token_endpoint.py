"""Integration tests for POST /api/banking/ws-token.

Exercises the full Lauren request pipeline (SignatureGuard → WsTokenController)
to verify that:
- Valid signed request → 200 with a non-empty token
- Missing X-Signature header → 401
- Wrong signature → 401
- Tampered body → 401
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

os.environ.setdefault("PAYLOAD_SECRET", "ws-integration-secret")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy-key")

SECRET = os.environ["PAYLOAD_SECRET"]
_ENDPOINT = "/api/banking/ws-token"


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture(scope="module")
def app():
    from app.app_module import AppModule
    from app.middlewares.cors_middleware import CorsMiddleware
    from lauren import LaurenFactory

    return LaurenFactory.create(AppModule, global_middlewares=[CorsMiddleware])


@pytest_asyncio.fixture()
async def client(app):
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


_BODY = json.dumps({"user_id": "alice"}).encode()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestWsTokenHappyPath:
    @pytest.mark.asyncio
    async def test_valid_request_returns_200(self, client):
        resp = await client.post(
            _ENDPOINT,
            content=_BODY,
            headers={
                "content-type": "application/json",
                "x-signature": _sign(_BODY),
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_contains_token_field(self, client):
        resp = await client.post(
            _ENDPOINT,
            content=_BODY,
            headers={
                "content-type": "application/json",
                "x-signature": _sign(_BODY),
            },
        )
        data = resp.json()
        assert "token" in data
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 0

    @pytest.mark.asyncio
    async def test_token_contains_dot_separator(self, client):
        resp = await client.post(
            _ENDPOINT,
            content=_BODY,
            headers={
                "content-type": "application/json",
                "x-signature": _sign(_BODY),
            },
        )
        token = resp.json()["token"]
        assert "." in token

    @pytest.mark.asyncio
    async def test_different_users_get_different_tokens(self, client):
        alice_body = json.dumps({"user_id": "alice"}).encode()
        bob_body = json.dumps({"user_id": "bob"}).encode()

        r1 = await client.post(
            _ENDPOINT,
            content=alice_body,
            headers={
                "content-type": "application/json",
                "x-signature": _sign(alice_body),
            },
        )
        r2 = await client.post(
            _ENDPOINT,
            content=bob_body,
            headers={
                "content-type": "application/json",
                "x-signature": _sign(bob_body),
            },
        )
        assert r1.json()["token"] != r2.json()["token"]


# ---------------------------------------------------------------------------
# Missing / wrong signature
# ---------------------------------------------------------------------------


class TestWsTokenAuthFailures:
    @pytest.mark.asyncio
    async def test_missing_signature_returns_401(self, client):
        resp = await client.post(
            _ENDPOINT,
            content=_BODY,
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_signature_returns_401(self, client):
        resp = await client.post(
            _ENDPOINT,
            content=_BODY,
            headers={
                "content-type": "application/json",
                "x-signature": "a" * 64,
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_tampered_body_returns_401(self, client):
        # Sign original body but send a different body
        original = json.dumps({"user_id": "alice"}).encode()
        tampered = json.dumps({"user_id": "bob"}).encode()
        resp = await client.post(
            _ENDPOINT,
            content=tampered,
            headers={
                "content-type": "application/json",
                "x-signature": _sign(original),
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_secret_returns_401(self, client):
        resp = await client.post(
            _ENDPOINT,
            content=_BODY,
            headers={
                "content-type": "application/json",
                "x-signature": _sign(_BODY, secret="wrong-secret"),
            },
        )
        assert resp.status_code == 401
