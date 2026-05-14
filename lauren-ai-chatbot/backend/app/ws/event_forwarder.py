"""EventForwarder — routes agent lifecycle events to WebSocket clients.

Architecture
------------
Each incoming HTTP chat request sets the ``current_user_id`` ContextVar
before calling ``AgentRunner.run()``.  ``asyncio.gather`` (used by
``SignalBus.emit``) copies ContextVar state into every spawned task, so
signal handlers can call ``current_user_id.get()`` to target the right
WebSocket connections.

Balance-change callbacks are fired by ``BankDatabase`` after a successful
transfer and broadcast to all connected clients so every user sees live
balance updates regardless of who initiated the transfer.
"""

from __future__ import annotations

import asyncio
from typing import Any

from lauren import Scope, injectable
from lauren.websockets import WebSocket
from lauren_ai import AgentRunComplete, ModelCallComplete, ToolCallComplete, ToolCallStarted

from app.ai.signals import GuardrailTriggered, signal_bus
from app.banking.bank_db import BankDatabase, Transaction
from app.ws.context import current_user_id


@injectable(scope=Scope.SINGLETON)
class EventForwarder:
    """Singleton that maintains per-user WebSocket registrations and routes events."""

    def __init__(self, db: BankDatabase) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

        # Clear any stale handlers that a previous EventForwarder instance may
        # have registered on the same module-level signal_bus singleton.  This
        # prevents N-times duplication when LaurenFactory.create() is called
        # multiple times in the same Python process (hot-reload in development,
        # multiple test-module fixtures running in the same pytest session).
        # EventForwarder is the only subscriber for these event types so
        # clearing is safe.  In normal single-run production this is a no-op.
        for _et in (
            ModelCallComplete,
            ToolCallStarted,
            ToolCallComplete,
            AgentRunComplete,
            GuardrailTriggered,
        ):
            signal_bus.clear(_et)

        # Register agent lifecycle signal handlers once at construction time
        signal_bus.on(ModelCallComplete)(self._on_model_complete)
        signal_bus.on(ToolCallStarted)(self._on_tool_started)
        signal_bus.on(ToolCallComplete)(self._on_tool_complete)
        signal_bus.on(AgentRunComplete)(self._on_run_complete)
        signal_bus.on(GuardrailTriggered)(self._on_guardrail_triggered)

        # Register balance-change listener on the shared BankDatabase instance
        db.add_transfer_listener(self._on_transfer)

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def register(self, user_id: str, ws: WebSocket) -> None:
        """Add *ws* to the set of connections for *user_id*."""
        async with self._lock:
            self._connections.setdefault(user_id, []).append(ws)

    async def unregister(self, user_id: str, ws: WebSocket) -> None:
        """Remove *ws* from the set of connections for *user_id*."""
        async with self._lock:
            bucket = self._connections.get(user_id)
            if bucket and ws in bucket:
                bucket.remove(ws)

    # ── Sending helpers ───────────────────────────────────────────────────────

    async def send_to_user(self, user_id: str, payload: dict[str, Any]) -> None:
        """Send *payload* to every WebSocket registered for *user_id*."""
        async with self._lock:
            targets = list(self._connections.get(user_id, []))
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                bucket = self._connections.get(user_id, [])
                for ws in dead:
                    if ws in bucket:
                        bucket.remove(ws)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Send *payload* to every connected WebSocket across all users."""
        async with self._lock:
            all_ws = [ws for bucket in self._connections.values() for ws in bucket]
        for ws in all_ws:
            try:
                await ws.send_json(payload)
            except Exception:
                pass

    # ── Signal handlers ───────────────────────────────────────────────────────

    async def _on_model_complete(self, event: ModelCallComplete) -> None:
        user_id = current_user_id.get()
        if not user_id:
            return
        usage = event.usage
        await self.send_to_user(
            user_id,
            {
                "type": "token_usage",
                "model": event.model,
                "input_tokens": usage.input_tokens if usage else 0,
                "output_tokens": usage.output_tokens if usage else 0,
                "cost_usd": event.cost_usd,
                "duration_ms": round(event.duration_ms),
            },
        )

    async def _on_tool_started(self, event: ToolCallStarted) -> None:
        user_id = current_user_id.get()
        if not user_id:
            return
        await self.send_to_user(
            user_id,
            {
                "type": "tool_started",
                "tool_name": event.tool_name,
                "tool_use_id": event.tool_use_id,
            },
        )

    async def _on_tool_complete(self, event: ToolCallComplete) -> None:
        user_id = current_user_id.get()
        if not user_id:
            return
        await self.send_to_user(
            user_id,
            {
                "type": "tool_complete",
                "tool_name": event.tool_name,
                "tool_use_id": event.tool_use_id,
                "success": event.success,
                "duration_ms": round(event.duration_ms),
                "error": event.error,
            },
        )

    async def _on_run_complete(self, event: AgentRunComplete) -> None:
        user_id = current_user_id.get()
        if not user_id:
            return
        usage = event.total_usage
        await self.send_to_user(
            user_id,
            {
                "type": "run_complete",
                "turns": event.turns,
                "total_cost_usd": event.total_cost_usd,
                "total_tokens": (usage.input_tokens + usage.output_tokens) if usage else 0,
            },
        )

    async def _on_guardrail_triggered(self, event: GuardrailTriggered) -> None:
        user_id = current_user_id.get()
        if not user_id:
            return
        await self.send_to_user(
            user_id,
            {
                "type": "guardrail_triggered",
                "guardrail_name": event.guardrail_name,
                "agent_name": event.agent_name,
                "violation": event.violation,
                "passed": event.passed,
            },
        )

    # ── Database callback ─────────────────────────────────────────────────────

    async def _on_transfer(self, tx: Transaction, from_balance: float, to_balance: float) -> None:
        """Broadcast balance update to all connected users after a transfer."""
        await self.broadcast(
            {
                "type": "balance_changed",
                "from_user": tx.from_user,
                "to_user": tx.to_user,
                "amount": tx.amount,
                "balances": {
                    tx.from_user: from_balance,
                    tx.to_user: to_balance,
                },
            }
        )
