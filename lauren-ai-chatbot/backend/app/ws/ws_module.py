"""WsModule — WebSocket infrastructure for real-time banking events.

Provides:
* ``EventForwarder`` — singleton that routes agent signals to WS clients
* ``WsTokenService`` — issues/verifies short-lived WS auth tokens
* ``BankingWsGateway`` — WebSocket controller at /ws/banking
* ``WsTokenController`` — HTTP controller at POST /api/banking/ws-token

Imports:
* ``CryptoModule`` — for ``CryptoService`` and ``SignatureGuard``
* ``BankingModule`` — for the ``BankDatabase`` singleton
"""

from __future__ import annotations

from lauren import module

from app.banking.banking_module import BankingModule
from app.crypto.crypto_module import CryptoModule
from app.ws.event_forwarder import EventForwarder
from app.ws.token_service import WsTokenService
from app.ws.ws_gateway import BankingWsGateway
from app.ws.ws_token_controller import WsTokenController


@module(
    imports=[CryptoModule, BankingModule],
    providers=[EventForwarder, WsTokenService],
    controllers=[BankingWsGateway, WsTokenController],
    exports=[EventForwarder],
)
class WsModule:
    """Real-time WebSocket module for live banking events."""
