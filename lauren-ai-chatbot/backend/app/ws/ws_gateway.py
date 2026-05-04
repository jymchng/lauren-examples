"""BankingWsGateway — WebSocket gateway for real-time banking events.

Authentication
--------------
Clients connect with a short-lived token in the query string::

    ws://host/ws/banking?token=<token>

The token is issued by ``WsTokenController`` (POST /api/banking/ws-token)
and is valid for 120 seconds — enough time for the browser to complete the
handshake after receiving it.

Events pushed to connected clients
-----------------------------------
* ``token_usage`` — after each LLM call (input/output tokens, cost)
* ``tool_started`` — when a tool call is dispatched
* ``tool_complete`` — when a tool call finishes (success or error)
* ``run_complete`` — when the full agent run finishes (total cost, turns)
* ``balance_changed`` — broadcast to ALL users when any transfer occurs
"""

from __future__ import annotations

from lauren import Query
from lauren.websockets import (
    WebSocket,
    WebSocketDisconnect,
    on_connect,
    on_disconnect,
    ws_controller,
)

from app.ws.event_forwarder import EventForwarder
from app.ws.token_service import WsTokenService


@ws_controller("/ws/banking")
class BankingWsGateway:
    """WebSocket gateway: authenticates via short-lived token then forwards events."""

    def __init__(self, forwarder: EventForwarder, token_service: WsTokenService) -> None:
        self._forwarder = forwarder
        self._token_service = token_service
        self._user_id: str | None = None

    @on_connect
    async def connect(self, ws: WebSocket, token: Query[str]) -> None:
        """Verify the token and register this connection for event delivery."""
        user_id = self._token_service.verify_token(token)
        if not user_id:
            await ws.close(code=4401, reason="invalid or expired token")
            raise WebSocketDisconnect("unauthorized", close_code=4401)
        self._user_id = user_id
        await self._forwarder.register(user_id, ws)

    @on_disconnect
    async def disconnect(self, ws: WebSocket) -> None:
        """Unregister this connection on close."""
        if self._user_id:
            await self._forwarder.unregister(self._user_id, ws)
