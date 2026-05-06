# NOTE: Do NOT add `from __future__ import annotations` to this file.
# These constants are imported by @tool() files where PEP 563 must not apply.
"""Canonical agent name constants.

Used as the ``name=`` argument in ``@agent()`` decorators and referenced by
handoff tools without importing the agent classes themselves (avoiding circular
imports).  A single source of truth keeps display names consistent across the
backend and WebSocket events.
"""

CRM_AGENT_NAME_EN: str = "Banking CRM Agent (English)"
CRM_AGENT_NAME_ZH: str = "Banking CRM Agent (Mandarin)"
TRANSFER_AGENT_NAME_EN: str = "Banking Transfer Agent (English)"
TRANSFER_AGENT_NAME_ZH: str = "Banking Transfer Agent (Mandarin)"

# Backward-compatible aliases — English is the default language.
CRM_AGENT_NAME = CRM_AGENT_NAME_EN
TRANSFER_AGENT_NAME = TRANSFER_AGENT_NAME_EN
