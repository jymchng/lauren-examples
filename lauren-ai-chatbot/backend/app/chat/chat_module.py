"""ChatModule — groups the chat controllers, agent controller, metrics, service."""

from __future__ import annotations

from lauren import module

from app.ai.ai_module import AIModule
from app.banking.banking_module import BankingModule
from app.chat.agent_controller import AgentController
from app.chat.banking_controller import BankingChatController
from app.chat.chat_controller import ChatController
from app.chat.chat_service import ChatService
from app.crypto.crypto_module import CryptoModule
from app.metrics.metrics_controller import MetricsController
from app.team.team_module import TeamModule


@module(
    imports=[CryptoModule, AIModule, BankingModule, TeamModule],
    controllers=[
        ChatController,
        AgentController,
        BankingChatController,
        MetricsController,
    ],
    providers=[ChatService],
)
class ChatModule:
    pass
