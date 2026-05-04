"""WebSocket context variable for the current authenticated user.

Set by BankingChatController before calling AgentRunner.run() so signal
handlers fired during the agent loop can route events to the right client.
"""

from __future__ import annotations

from contextvars import ContextVar

# Holds the authenticated user_id for the current agent run.
# asyncio.gather() copies the ContextVar context into spawned tasks, so
# this value is visible inside SignalBus handlers called via emit().
current_user_id: ContextVar[str | None] = ContextVar("ws_current_user_id", default=None)
