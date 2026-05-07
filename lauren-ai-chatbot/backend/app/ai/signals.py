"""Shared SignalBus singleton and custom signal classes for the chatbot application.

Centralising the bus here avoids circular imports between ``main.py``
and ``ai_module.py``, both of which need access to the same bus instance.
"""

from __future__ import annotations

from dataclasses import dataclass

from lauren_ai import SignalBus

signal_bus: SignalBus = SignalBus()


@dataclass
class GuardrailTriggered:
    """Fired by ``AgentScopeGuard`` when an off-topic response is intercepted."""

    guardrail_name: str
    agent_name: str
    violation: str
