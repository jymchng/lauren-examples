"""ChatModule — groups the chat controller, agent controller, metrics, service, and its dependencies."""

from __future__ import annotations

from lauren import module

from app.ai.ai_module import AIModule
from app.chat.agent_controller import AgentController
from app.chat.chat_controller import ChatController
from app.chat.chat_service import ChatService
from app.crypto.crypto_module import CryptoModule
from app.metrics.metrics_controller import MetricsController


@module(
    imports=[CryptoModule, AIModule],
    controllers=[ChatController, AgentController, MetricsController],
    providers=[ChatService],
)
class ChatModule:
    pass
