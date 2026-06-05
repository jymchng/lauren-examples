"""Signals — single shared :class:`SignalBus` for the backend.

P0 fix: framework observability (issue 7.2).  The bus is wired into
``AIModule`` so every ``ModelCallComplete`` / ``AgentRunComplete`` is
emitted on a single, well-known bus.
"""

from __future__ import annotations

from lauren_ai import SignalBus

signal_bus: SignalBus = SignalBus()
