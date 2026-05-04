"""Root application module — wires together all feature modules."""

from __future__ import annotations

from lauren import module

from app.banking.banking_module import BankingModule
from app.health.health_module import HealthModule
from app.ws.ws_module import WsModule


from app.ai.ai_module import AIModule
from app.banking.banking_module import BankingModule
from app.metrics.metrics_module import MetricsModule


@module(imports=[BankingModule, HealthModule, WsModule, AIModule, MetricsModule])
class AppModule:
    pass
