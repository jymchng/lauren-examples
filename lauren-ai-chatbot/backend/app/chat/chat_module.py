"""ChatModule — groups the banking chat controller and metrics."""

from __future__ import annotations

from lauren import module

from app.ai.ai_module import AIModule
from app.banking.banking_module import BankingModule
from app.chat.banking_controller import BankingChatController
from app.crypto.crypto_module import CryptoModule
from app.metrics.metrics_controller import MetricsController


@module(
    imports=[CryptoModule, AIModule, BankingModule],
    controllers=[
        BankingChatController,
        MetricsController,
    ],
)
class ChatModule:
    pass
