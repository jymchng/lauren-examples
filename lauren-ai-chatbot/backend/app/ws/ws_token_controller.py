"""WsTokenController — issues short-lived WebSocket authentication tokens.

The Next.js proxy calls this endpoint (POST /api/banking/ws-token) with an
HMAC-signed body containing the authenticated user_id.  On success it returns
a short-lived token that the browser passes as ?token=... when connecting to
the WebSocket gateway at /ws/banking.
"""

from __future__ import annotations

import msgspec

from lauren import Json, controller, post, use_guards

from app.crypto.signature_guard import SignatureGuard
from app.ws.token_service import WsTokenService


class WsTokenRequest(msgspec.Struct):
    user_id: str


@use_guards(SignatureGuard)
@controller("/api/banking")
class WsTokenController:
    """Issues a short-lived WebSocket auth token for the given user."""

    def __init__(self, token_service: WsTokenService) -> None:
        self._token_service = token_service

    @post("/ws-token")
    async def issue_token(self, body: Json[WsTokenRequest]) -> dict:
        return {"token": self._token_service.create_token(body.user_id)}
