"""TeamModule — wires the team controller and its dependencies."""

from __future__ import annotations

from lauren import module

from app.ai.ai_module import AIModule
from app.crypto.crypto_module import CryptoModule
from app.team.team_controller import TeamController


@module(
    imports=[CryptoModule, AIModule],
    controllers=[TeamController],
)
class TeamModule:
    pass
