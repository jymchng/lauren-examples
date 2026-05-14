"""Shared SignalBus singleton and custom signal classes for the chatbot application.

Centralising the bus here avoids circular imports between ``main.py``
and ``ai_module.py``, both of which need access to the same bus instance.
"""

from __future__ import annotations

import msgspec

from lauren_ai import SignalBus

signal_bus: SignalBus = SignalBus()


class GuardrailTriggered(msgspec.Struct):
    """Fired by guardrails after every response evaluation.

    ``passed=True`` when the response was clean (guardrail did not fire).
    ``passed=False`` when the guardrail fired and replaced the response.
    Both cases appear in the live activity feed so operators can monitor
    guardrail coverage, not just interventions.
    """

    guardrail_name: str
    agent_name: str
    violation: str
    passed: bool = False
