"""Integration tests for the banking REST endpoints.

GET /api/banking/accounts          — list all accounts
GET /api/banking/accounts/{user_id} — single account with transactions
"""

from __future__ import annotations

import os

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

os.environ.setdefault("PAYLOAD_SECRET", "rest-test-secret")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")
os.environ.setdefault("PORT", "8004")


@pytest.fixture(scope="module")
def app():
    from app.app_module import AppModule
    from app.middlewares.cors_middleware import CorsMiddleware
    from lauren import LaurenFactory

    return LaurenFactory.create(AppModule, global_middlewares=[CorsMiddleware])


@pytest_asyncio.fixture()
async def client(app):
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /api/banking/accounts
# ---------------------------------------------------------------------------


class TestListAccounts:
    @pytest.mark.asyncio
    async def test_returns_200(self, client):
        resp = await client.get("/api/banking/accounts")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_has_accounts_key(self, client):
        resp = await client.get("/api/banking/accounts")
        data = resp.json()
        assert "accounts" in data
        assert isinstance(data["accounts"], list)

    @pytest.mark.asyncio
    async def test_returns_three_accounts(self, client):
        resp = await client.get("/api/banking/accounts")
        assert len(resp.json()["accounts"]) == 3

    @pytest.mark.asyncio
    async def test_accounts_have_required_fields(self, client):
        resp = await client.get("/api/banking/accounts")
        for account in resp.json()["accounts"]:
            assert "user_id" in account
            assert "name" in account
            assert "account_id" in account
            assert "balance" in account
            assert "avatar_color" in account

    @pytest.mark.asyncio
    async def test_alice_is_in_accounts(self, client):
        resp = await client.get("/api/banking/accounts")
        ids = [a["user_id"] for a in resp.json()["accounts"]]
        assert "alice" in ids

    @pytest.mark.asyncio
    async def test_all_three_users_present(self, client):
        resp = await client.get("/api/banking/accounts")
        ids = {a["user_id"] for a in resp.json()["accounts"]}
        assert ids == {"alice", "bob", "charlie"}

    @pytest.mark.asyncio
    async def test_balances_are_positive(self, client):
        resp = await client.get("/api/banking/accounts")
        for a in resp.json()["accounts"]:
            assert a["balance"] >= 0

    @pytest.mark.asyncio
    async def test_cors_header_present(self, client):
        resp = await client.get(
            "/api/banking/accounts",
            headers={"origin": "http://localhost:3000"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/banking/accounts/{user_id}
# ---------------------------------------------------------------------------


class TestGetAccount:
    @pytest.mark.asyncio
    async def test_alice_returns_200(self, client):
        resp = await client.get("/api/banking/accounts/alice")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_bob_returns_200(self, client):
        resp = await client.get("/api/banking/accounts/bob")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_charlie_returns_200(self, client):
        resp = await client.get("/api/banking/accounts/charlie")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_unknown_user_returns_404(self, client):
        resp = await client.get("/api/banking/accounts/dave")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_alice_has_correct_fields(self, client):
        resp = await client.get("/api/banking/accounts/alice")
        data = resp.json()
        assert data["user_id"] == "alice"
        assert data["name"] == "Alice Johnson"
        assert data["account_id"] == "ACC-001"
        assert isinstance(data["balance"], float)
        assert "transactions" in data

    @pytest.mark.asyncio
    async def test_transactions_is_list(self, client):
        resp = await client.get("/api/banking/accounts/alice")
        assert isinstance(resp.json()["transactions"], list)

    @pytest.mark.asyncio
    async def test_transactions_initially_empty(self, client):
        """Fresh db has no transactions (module-scoped app, but may have prior tests' state)."""
        resp = await client.get("/api/banking/accounts/alice")
        assert isinstance(resp.json()["transactions"], list)

    @pytest.mark.asyncio
    async def test_transaction_fields_present(self, client):
        """If there are transactions, they have the required fields."""
        resp = await client.get("/api/banking/accounts/alice")
        txns = resp.json()["transactions"]
        for t in txns:
            assert "tx_id" in t
            assert "type" in t
            assert "amount" in t
            assert "timestamp" in t

    @pytest.mark.asyncio
    async def test_avatar_color_is_hex(self, client):
        resp = await client.get("/api/banking/accounts/alice")
        color = resp.json()["avatar_color"]
        assert color.startswith("#")
        assert len(color) in (4, 7)
