"""ActiveAgentModule — provides session-level agent routing state."""

from __future__ import annotations

from lauren import module

from app.ai.tools.active_agent_store import ActiveAgentStore


@module(
    providers=[ActiveAgentStore],
    exports=[ActiveAgentStore],
)
class ActiveAgentModule:
    """Provides ``ActiveAgentStore`` for conversation handoff routing."""
