"""Unit tests for EventForwarder — routes agent signals to WebSocket clients."""

from __future__ import annotations

import asyncio
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("PAYLOAD_SECRET", "test-secret-abc123")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")

from app.ws.context import current_user_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ws(*, fail: bool = False) -> MagicMock:
    """Return a WebSocket mock. If fail=True, send_json raises an exception."""
    ws = MagicMock()
    if fail:
        ws.send_json = AsyncMock(side_effect=ConnectionResetError("dead"))
    else:
        ws.send_json = AsyncMock()
    return ws


def _make_db() -> MagicMock:
    """Return a BankDatabase mock with add_transfer_listener as a no-op."""
    db = MagicMock()
    db.add_transfer_listener = MagicMock()
    return db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    return _make_db()


@pytest.fixture()
def forwarder(db):
    """EventForwarder with mocked signal bus and DB."""
    with patch("app.ws.event_forwarder.signal_bus") as mock_bus:
        mock_bus.on = MagicMock(return_value=lambda fn: fn)
        from app.ws.event_forwarder import EventForwarder
        fwd = EventForwarder(db)
    return fwd


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    @pytest.mark.asyncio
    async def test_register_adds_connection(self, forwarder):
        ws = _make_ws()
        await forwarder.register("alice", ws)
        assert ws in forwarder._connections["alice"]

    @pytest.mark.asyncio
    async def test_register_multiple_same_user(self, forwarder):
        ws1, ws2 = _make_ws(), _make_ws()
        await forwarder.register("alice", ws1)
        await forwarder.register("alice", ws2)
        assert len(forwarder._connections["alice"]) == 2

    @pytest.mark.asyncio
    async def test_unregister_removes_connection(self, forwarder):
        ws = _make_ws()
        await forwarder.register("alice", ws)
        await forwarder.unregister("alice", ws)
        assert ws not in forwarder._connections.get("alice", [])

    @pytest.mark.asyncio
    async def test_unregister_unknown_user_is_noop(self, forwarder):
        ws = _make_ws()
        # Should not raise
        await forwarder.unregister("nobody", ws)

    @pytest.mark.asyncio
    async def test_unregister_unknown_ws_is_noop(self, forwarder):
        ws1, ws2 = _make_ws(), _make_ws()
        await forwarder.register("alice", ws1)
        # Unregistering ws2 which was never registered — should be safe
        await forwarder.unregister("alice", ws2)
        assert ws1 in forwarder._connections["alice"]


# ---------------------------------------------------------------------------
# send_to_user
# ---------------------------------------------------------------------------


class TestSendToUser:
    @pytest.mark.asyncio
    async def test_sends_to_registered_user(self, forwarder):
        ws = _make_ws()
        await forwarder.register("alice", ws)
        await forwarder.send_to_user("alice", {"type": "test"})
        ws.send_json.assert_awaited_once_with({"type": "test"})

    @pytest.mark.asyncio
    async def test_sends_to_all_connections_for_user(self, forwarder):
        ws1, ws2 = _make_ws(), _make_ws()
        await forwarder.register("alice", ws1)
        await forwarder.register("alice", ws2)
        await forwarder.send_to_user("alice", {"type": "test"})
        ws1.send_json.assert_awaited_once()
        ws2.send_json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_noop_for_unregistered_user(self, forwarder):
        # Should not raise
        await forwarder.send_to_user("nobody", {"type": "test"})

    @pytest.mark.asyncio
    async def test_dead_connection_removed_silently(self, forwarder):
        dead = _make_ws(fail=True)
        alive = _make_ws()
        await forwarder.register("alice", dead)
        await forwarder.register("alice", alive)
        await forwarder.send_to_user("alice", {"type": "test"})
        # Alive one gets the message; dead one is evicted
        alive.send_json.assert_awaited_once()
        assert dead not in forwarder._connections.get("alice", [])

    @pytest.mark.asyncio
    async def test_does_not_send_to_other_users(self, forwarder):
        alice_ws = _make_ws()
        bob_ws = _make_ws()
        await forwarder.register("alice", alice_ws)
        await forwarder.register("bob", bob_ws)
        await forwarder.send_to_user("alice", {"type": "test"})
        alice_ws.send_json.assert_awaited_once()
        bob_ws.send_json.assert_not_called()


# ---------------------------------------------------------------------------
# broadcast
# ---------------------------------------------------------------------------


class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcasts_to_all_users(self, forwarder):
        alice_ws = _make_ws()
        bob_ws = _make_ws()
        await forwarder.register("alice", alice_ws)
        await forwarder.register("bob", bob_ws)
        await forwarder.broadcast({"type": "balance_changed"})
        alice_ws.send_json.assert_awaited_once_with({"type": "balance_changed"})
        bob_ws.send_json.assert_awaited_once_with({"type": "balance_changed"})

    @pytest.mark.asyncio
    async def test_broadcast_with_no_connections_is_noop(self, forwarder):
        # Should not raise
        await forwarder.broadcast({"type": "test"})

    @pytest.mark.asyncio
    async def test_dead_broadcast_target_does_not_crash(self, forwarder):
        dead = _make_ws(fail=True)
        await forwarder.register("alice", dead)
        await forwarder.broadcast({"type": "test"})  # must not raise


# ---------------------------------------------------------------------------
# Signal handler: _on_model_complete
# ---------------------------------------------------------------------------


class TestOnModelComplete:
    @pytest.mark.asyncio
    async def test_sends_token_usage_to_current_user(self, forwarder):
        ws = _make_ws()
        await forwarder.register("alice", ws)

        usage = MagicMock()
        usage.input_tokens = 10
        usage.output_tokens = 20

        event = MagicMock()
        event.model = "claude-opus-4-6"
        event.usage = usage
        event.cost_usd = 0.001
        event.duration_ms = 500.0

        token = current_user_id.set("alice")
        try:
            await forwarder._on_model_complete(event)
        finally:
            current_user_id.reset(token)

        ws.send_json.assert_awaited_once()
        payload = ws.send_json.call_args[0][0]
        assert payload["type"] == "token_usage"
        assert payload["input_tokens"] == 10
        assert payload["output_tokens"] == 20
        assert payload["model"] == "claude-opus-4-6"

    @pytest.mark.asyncio
    async def test_noop_when_no_current_user(self, forwarder):
        ws = _make_ws()
        await forwarder.register("alice", ws)

        event = MagicMock()
        # current_user_id defaults to None
        token = current_user_id.set(None)
        try:
            await forwarder._on_model_complete(event)
        finally:
            current_user_id.reset(token)

        ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_none_usage_gracefully(self, forwarder):
        ws = _make_ws()
        await forwarder.register("alice", ws)

        event = MagicMock()
        event.usage = None
        event.cost_usd = 0.0
        event.duration_ms = 100.0
        event.model = "test"

        token = current_user_id.set("alice")
        try:
            await forwarder._on_model_complete(event)
        finally:
            current_user_id.reset(token)

        payload = ws.send_json.call_args[0][0]
        assert payload["input_tokens"] == 0
        assert payload["output_tokens"] == 0


# ---------------------------------------------------------------------------
# Signal handler: _on_tool_started
# ---------------------------------------------------------------------------


class TestOnToolStarted:
    @pytest.mark.asyncio
    async def test_sends_tool_started_event(self, forwarder):
        ws = _make_ws()
        await forwarder.register("alice", ws)

        event = MagicMock()
        event.tool_name = "transfer_funds"
        event.tool_use_id = "toolu_001"

        token = current_user_id.set("alice")
        try:
            await forwarder._on_tool_started(event)
        finally:
            current_user_id.reset(token)

        payload = ws.send_json.call_args[0][0]
        assert payload["type"] == "tool_started"
        assert payload["tool_name"] == "transfer_funds"
        assert payload["tool_use_id"] == "toolu_001"

    @pytest.mark.asyncio
    async def test_noop_when_no_current_user(self, forwarder):
        ws = _make_ws()
        await forwarder.register("alice", ws)
        event = MagicMock()
        token = current_user_id.set(None)
        try:
            await forwarder._on_tool_started(event)
        finally:
            current_user_id.reset(token)
        ws.send_json.assert_not_called()


# ---------------------------------------------------------------------------
# Signal handler: _on_tool_complete
# ---------------------------------------------------------------------------


class TestOnToolComplete:
    @pytest.mark.asyncio
    async def test_sends_tool_complete_success(self, forwarder):
        ws = _make_ws()
        await forwarder.register("bob", ws)

        event = MagicMock()
        event.tool_name = "get_balance"
        event.tool_use_id = "toolu_002"
        event.success = True
        event.duration_ms = 42.0
        event.error = None

        token = current_user_id.set("bob")
        try:
            await forwarder._on_tool_complete(event)
        finally:
            current_user_id.reset(token)

        payload = ws.send_json.call_args[0][0]
        assert payload["type"] == "tool_complete"
        assert payload["success"] is True
        assert payload["duration_ms"] == 42
        assert payload["error"] is None

    @pytest.mark.asyncio
    async def test_sends_tool_complete_failure(self, forwarder):
        ws = _make_ws()
        await forwarder.register("bob", ws)

        event = MagicMock()
        event.tool_name = "transfer_funds"
        event.tool_use_id = "toolu_003"
        event.success = False
        event.duration_ms = 10.0
        event.error = "Insufficient funds"

        token = current_user_id.set("bob")
        try:
            await forwarder._on_tool_complete(event)
        finally:
            current_user_id.reset(token)

        payload = ws.send_json.call_args[0][0]
        assert payload["success"] is False
        assert payload["error"] == "Insufficient funds"


# ---------------------------------------------------------------------------
# Signal handler: _on_run_complete
# ---------------------------------------------------------------------------


class TestOnRunComplete:
    @pytest.mark.asyncio
    async def test_sends_run_complete_event(self, forwarder):
        ws = _make_ws()
        await forwarder.register("charlie", ws)

        usage = MagicMock()
        usage.input_tokens = 100
        usage.output_tokens = 50

        event = MagicMock()
        event.turns = 3
        event.total_cost_usd = 0.005
        event.total_usage = usage

        token = current_user_id.set("charlie")
        try:
            await forwarder._on_run_complete(event)
        finally:
            current_user_id.reset(token)

        payload = ws.send_json.call_args[0][0]
        assert payload["type"] == "run_complete"
        assert payload["turns"] == 3
        assert payload["total_cost_usd"] == 0.005
        assert payload["total_tokens"] == 150

    @pytest.mark.asyncio
    async def test_handles_none_usage(self, forwarder):
        ws = _make_ws()
        await forwarder.register("charlie", ws)

        event = MagicMock()
        event.turns = 1
        event.total_cost_usd = 0.0
        event.total_usage = None

        token = current_user_id.set("charlie")
        try:
            await forwarder._on_run_complete(event)
        finally:
            current_user_id.reset(token)

        payload = ws.send_json.call_args[0][0]
        assert payload["total_tokens"] == 0


# ---------------------------------------------------------------------------
# Balance-change callback: _on_transfer
# ---------------------------------------------------------------------------


class TestOnTransfer:
    @pytest.mark.asyncio
    async def test_broadcasts_balance_changed_to_all(self, forwarder):
        alice_ws = _make_ws()
        bob_ws = _make_ws()
        await forwarder.register("alice", alice_ws)
        await forwarder.register("bob", bob_ws)

        from app.banking.bank_db import Transaction
        tx = Transaction(
            tx_id="TXN-001",
            from_user="alice",
            to_user="bob",
            amount=100.0,
            timestamp="2024-01-01T00:00:00Z",
            description="test transfer",
        )

        await forwarder._on_transfer(tx, 4900.0, 3300.0)

        for ws in (alice_ws, bob_ws):
            ws.send_json.assert_awaited_once()
            payload = ws.send_json.call_args[0][0]
            assert payload["type"] == "balance_changed"
            assert payload["from_user"] == "alice"
            assert payload["to_user"] == "bob"
            assert payload["amount"] == 100.0
            assert payload["balances"] == {"alice": 4900.0, "bob": 3300.0}

    @pytest.mark.asyncio
    async def test_transfer_broadcast_with_no_connections_is_noop(self, forwarder):
        from app.banking.bank_db import Transaction
        tx = Transaction(
            tx_id="TXN-002",
            from_user="alice",
            to_user="bob",
            amount=50.0,
            timestamp="2024-01-01T00:00:00Z",
            description="no-clients test",
        )
        # Must not raise even when no clients are connected
        await forwarder._on_transfer(tx, 4950.0, 3250.0)
