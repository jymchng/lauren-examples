"""Root application module — wires together all feature modules."""

from __future__ import annotations

from lauren import module

from app.chat.chat_module import ChatModule
from app.health.health_module import HealthModule


@module(imports=[ChatModule, HealthModule])
class AppModule:
    pass
