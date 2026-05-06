"""ActiveAgentStore — session-level routing state for conversation handoff.

Maps ``conversation_id`` → active agent name so the controller can route each
incoming chat message to the correct agent.  Defaults to the CRM Agent when no
handoff has occurred for a given conversation.
"""

from __future__ import annotations

from lauren import Scope, injectable


@injectable(scope=Scope.SINGLETON)
class ActiveAgentStore:
    """Tracks which agent currently owns each conversation.

    Keyed by ``conversation_id`` (a UUID supplied by the frontend).  Thread-safe
    for single-process deployments; replace with a Redis-backed store for
    multi-process deployments.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._pending_summary: dict[str, str] = {}

    def get(self, conversation_id: str, default: str) -> str:
        """Return the active agent name for *conversation_id*, or *default*."""
        return self._store.get(conversation_id, default)

    def set(self, conversation_id: str, agent_name: str) -> None:
        """Set *agent_name* as the active agent for *conversation_id*."""
        self._store[conversation_id] = agent_name

    def reset(self, conversation_id: str) -> None:
        """Remove the routing entry, reverting to the default agent."""
        self._store.pop(conversation_id, None)

    def set_pending_summary(self, conversation_id: str, summary: str) -> None:
        """Store *summary* to be consumed once by the controller on the next handoff."""
        self._pending_summary[conversation_id] = summary

    def pop_pending_summary(self, conversation_id: str) -> str:
        """Return and clear the pending summary, or '' if none was set."""
        return self._pending_summary.pop(conversation_id, "")
