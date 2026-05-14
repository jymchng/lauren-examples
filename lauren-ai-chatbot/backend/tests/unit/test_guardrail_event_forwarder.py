"""Tests for EventForwarder guardrail event handling.

Specifically tests _on_guardrail_triggered() and the GuardrailTriggered signal
subscription, payload format, and WebSocket delivery.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("PAYLOAD_SECRET", "test-secret-abc123")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")

from app.ai.signals import GuardrailTriggered
from app.ws.context import current_user_id

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ws(*, fail: bool = False) -> MagicMock:
    ws = MagicMock()
    ws.send_json = AsyncMock(side_effect=ConnectionResetError() if fail else None)
    return ws


def _make_db() -> MagicMock:
    db = MagicMock()
    db.add_transfer_listener = MagicMock()
    return db


def _make_forwarder():
    """Return a real EventForwarder with real signal bus (not patched)."""
    from app.ws.event_forwarder import EventForwarder

    return EventForwarder(_make_db())


def _make_forwarder_patched_bus():
    """Return EventForwarder with patched bus so signal registrations are no-ops."""
    with patch("app.ws.event_forwarder.signal_bus") as mock_bus:
        mock_bus.on = MagicMock(return_value=lambda fn: fn)
        from app.ws.event_forwarder import EventForwarder

        fwd = EventForwarder(_make_db())
    return fwd


# ---------------------------------------------------------------------------
# Class 1 — TestGuardrailTriggeredSubscription (5 tests)
# ---------------------------------------------------------------------------


class TestGuardrailTriggeredSubscription:
    def test_event_forwarder_subscribes_to_guardrail_triggered_at_init(self):
        """EventForwarder must subscribe to GuardrailTriggered during __init__."""
        subscribed_types = []
        with patch("app.ws.event_forwarder.signal_bus") as bus:

            def capture_on(event_type):
                subscribed_types.append(event_type)
                return lambda fn: fn

            bus.on = capture_on
            from app.ws.event_forwarder import EventForwarder

            EventForwarder(_make_db())
        assert GuardrailTriggered in subscribed_types, (
            "EventForwarder must subscribe to GuardrailTriggered via signal_bus.on()"
        )

    def test_guardrail_triggered_handler_is_async_callable(self):
        fwd = _make_forwarder_patched_bus()
        handler = fwd._on_guardrail_triggered
        assert callable(handler)
        import inspect

        assert inspect.iscoroutinefunction(handler)

    def test_guardrail_triggered_signal_is_msgspec_struct(self):
        import msgspec

        assert issubclass(GuardrailTriggered, msgspec.Struct)

    def test_guardrail_triggered_has_all_required_fields(self):
        import msgspec

        fields = {f.name for f in msgspec.structs.fields(GuardrailTriggered)}
        assert "guardrail_name" in fields
        assert "agent_name" in fields
        assert "violation" in fields

    async def test_event_forwarder_handles_guardrail_triggered_without_error(self):
        fwd = _make_forwarder_patched_bus()
        event = GuardrailTriggered(
            guardrail_name="TestGuard",
            agent_name="Test Agent",
            violation="test violation",
        )
        # Should not raise even with no registered WebSocket connections
        await fwd._on_guardrail_triggered(event)


# ---------------------------------------------------------------------------
# Class 2 — TestGuardrailWebSocketPayload (6 tests)
# ---------------------------------------------------------------------------


class TestGuardrailWebSocketPayload:
    async def test_payload_type_is_guardrail_triggered(self):
        fwd = _make_forwarder_patched_bus()
        ws = _make_ws()
        token = current_user_id.set("alice")
        try:
            await fwd.register("alice", ws)
            event = GuardrailTriggered(
                guardrail_name="G",
                agent_name="A",
                violation="V",
            )
            await fwd._on_guardrail_triggered(event)
        finally:
            current_user_id.reset(token)
        payload = ws.send_json.call_args[0][0]
        assert payload["type"] == "guardrail_triggered"

    async def test_payload_contains_guardrail_name(self):
        fwd = _make_forwarder_patched_bus()
        ws = _make_ws()
        token = current_user_id.set("alice")
        try:
            await fwd.register("alice", ws)
            await fwd._on_guardrail_triggered(
                GuardrailTriggered(guardrail_name="SpecificGuard", agent_name="A", violation="V")
            )
        finally:
            current_user_id.reset(token)
        payload = ws.send_json.call_args[0][0]
        assert payload["guardrail_name"] == "SpecificGuard"

    async def test_payload_contains_agent_name(self):
        fwd = _make_forwarder_patched_bus()
        ws = _make_ws()
        token = current_user_id.set("alice")
        try:
            await fwd.register("alice", ws)
            await fwd._on_guardrail_triggered(
                GuardrailTriggered(guardrail_name="G", agent_name="Transfer Agent", violation="V")
            )
        finally:
            current_user_id.reset(token)
        payload = ws.send_json.call_args[0][0]
        assert payload["agent_name"] == "Transfer Agent"

    async def test_payload_contains_violation(self):
        fwd = _make_forwarder_patched_bus()
        ws = _make_ws()
        token = current_user_id.set("alice")
        try:
            await fwd.register("alice", ws)
            await fwd._on_guardrail_triggered(
                GuardrailTriggered(guardrail_name="G", agent_name="A", violation="branch hour detected")
            )
        finally:
            current_user_id.reset(token)
        payload = ws.send_json.call_args[0][0]
        assert payload["violation"] == "branch hour detected"

    async def test_payload_sent_to_correct_user(self):
        fwd = _make_forwarder_patched_bus()
        ws_alice = _make_ws()
        ws_bob = _make_ws()
        await fwd.register("alice", ws_alice)
        await fwd.register("bob", ws_bob)

        token = current_user_id.set("alice")
        try:
            await fwd._on_guardrail_triggered(GuardrailTriggered(guardrail_name="G", agent_name="A", violation="V"))
        finally:
            current_user_id.reset(token)

        ws_alice.send_json.assert_called_once()
        ws_bob.send_json.assert_not_called()

    async def test_no_payload_sent_when_no_user_id(self):
        """If ContextVar has no user_id, handler returns early without sending."""
        fwd = _make_forwarder_patched_bus()
        ws = _make_ws()
        await fwd.register("alice", ws)

        # Do NOT set current_user_id — it should be None/default
        await fwd._on_guardrail_triggered(GuardrailTriggered(guardrail_name="G", agent_name="A", violation="V"))

        ws.send_json.assert_not_called()


# ---------------------------------------------------------------------------
# Class 3 — TestGuardrailEventForwarderIntegration (4 tests)
# ---------------------------------------------------------------------------


class TestGuardrailEventForwarderIntegration:
    async def test_agent_scope_guard_signal_reaches_websocket(self):
        """Full chain: AgentScopeGuard fires → GuardrailTriggered signal → EventForwarder → ws.send_json."""
        from app.ai.guardrails.agent_scope_guard import AgentScopeGuard
        from app.ai.signals import signal_bus

        fwd = _make_forwarder()  # real EventForwarder with real bus
        ws = _make_ws()
        await fwd.register("alice", ws)

        guard = AgentScopeGuard(
            off_topic_phrases=("branch hour",),
            redirect_message="Redirect.",
            guardrail_name="TestGuard",
            agent_name="TestAgent",
        )

        from lauren_ai._guardrails._base import GuardrailContext

        ctx = GuardrailContext(agent_name="TestAgent")

        token = current_user_id.set("alice")
        try:
            await guard.check("branch hour is 9-5.", ctx)
            # Give signal bus time to call all handlers
            await asyncio.sleep(0)
        finally:
            current_user_id.reset(token)

        ws.send_json.assert_called()

    async def test_guardrail_payload_structure_complete(self):
        """Verify all four required keys are in the WS payload."""
        fwd = _make_forwarder_patched_bus()
        ws = _make_ws()
        token = current_user_id.set("alice")
        try:
            await fwd.register("alice", ws)
            await fwd._on_guardrail_triggered(GuardrailTriggered(guardrail_name="G", agent_name="A", violation="V"))
        finally:
            current_user_id.reset(token)
        payload = ws.send_json.call_args[0][0]
        for key in ("type", "guardrail_name", "agent_name", "violation"):
            assert key in payload, f"Missing key in payload: {key}"

    async def test_multiple_guardrail_events_all_delivered(self):
        """Two guardrail events for same user → two send_json calls."""
        fwd = _make_forwarder_patched_bus()
        ws = _make_ws()
        token = current_user_id.set("alice")
        try:
            await fwd.register("alice", ws)
            e1 = GuardrailTriggered(guardrail_name="G1", agent_name="A", violation="V1")
            e2 = GuardrailTriggered(guardrail_name="G2", agent_name="B", violation="V2")
            await fwd._on_guardrail_triggered(e1)
            await fwd._on_guardrail_triggered(e2)
        finally:
            current_user_id.reset(token)
        assert ws.send_json.call_count == 2

    async def test_different_users_guardrail_events_not_crossed(self):
        """Alice's guardrail event only goes to Alice, not Bob."""
        fwd = _make_forwarder_patched_bus()
        ws_alice = _make_ws()
        ws_bob = _make_ws()
        await fwd.register("alice", ws_alice)
        await fwd.register("bob", ws_bob)

        # Fire for Alice
        token = current_user_id.set("alice")
        try:
            await fwd._on_guardrail_triggered(GuardrailTriggered(guardrail_name="G", agent_name="A", violation="V"))
        finally:
            current_user_id.reset(token)

        # Fire for Bob
        token2 = current_user_id.set("bob")
        try:
            await fwd._on_guardrail_triggered(GuardrailTriggered(guardrail_name="G", agent_name="A", violation="V"))
        finally:
            current_user_id.reset(token2)

        assert ws_alice.send_json.call_count == 1
        assert ws_bob.send_json.call_count == 1
