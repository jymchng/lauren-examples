"""Shared SignalBus singleton for the chatbot application.

Centralising the bus here avoids circular imports between ``main.py``
and ``ai_module.py``, both of which need access to the same bus instance.
"""

from __future__ import annotations

from lauren_ai import SignalBus

signal_bus: SignalBus = SignalBus()
