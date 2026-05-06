"""WsPublicTokenController — issues WebSocket tokens for unauthenticated (public) clients.

No guard is applied — any visitor may obtain a public WS token.  The token
embeds the sentinel user_id ``"__public__"`` so the gateway registers the
connection under that key and the event forwarder routes public-session
agent events to it.
"""

from __future__ import annotations

from lauren import controller, post

from app.ws.token_service import WsTokenService

PUBLIC_WS_USER = "__public__"


@controller("/api/banking")
class WsPublicTokenController:
    """Issues a short-lived WS token for public (guest) clients — no authentication required."""

    def __init__(self, token_service: WsTokenService) -> None:
        self._token_service = token_service

    @post("/ws-token/public")
    async def issue_public_token(self) -> dict:
        return {"token": self._token_service.create_token(PUBLIC_WS_USER)}
