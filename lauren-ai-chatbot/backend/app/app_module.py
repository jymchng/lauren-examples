"""Root application module — wires together all feature modules."""

from __future__ import annotations

from lauren import module

from app.banking.banking_module import BankingModule
from app.chat.chat_module import ChatModule
from app.health.health_module import HealthModule
from app.team.team_module import TeamModule


@module(imports=[BankingModule, ChatModule, HealthModule, TeamModule])
class AppModule:
    pass
