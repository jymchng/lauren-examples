"""Canonical agent name constants.

Used as the ``name=`` argument in ``@agent()`` decorators and referenced by
handoff tools without importing the agent classes themselves (avoiding circular
imports).  A single source of truth keeps display names consistent across the
backend and WebSocket events.
"""

UNAUTH_CRM_AGENT_NAME: str = "Banking CRM Agent (Public)"
AUTH_CRM_AGENT_NAME: str = "Banking CRM Agent (Authenticated)"
TRANSFER_AGENT_NAME: str = "Banking Transfer Agent"
DISPUTES_AGENT_NAME: str = "Banking Disputes Agent"
