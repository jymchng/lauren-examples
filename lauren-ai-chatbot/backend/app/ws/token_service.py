"""WsTokenService — creates and verifies short-lived WebSocket auth tokens.

Token format: ``base64url(json_payload).hmac_signature``

The payload is ``{"uid": "<user_id>", "exp": <unix_seconds>}``.  The
signature is computed by the shared ``CryptoService`` (same HMAC-SHA256
key used for HTTP payload signing), so no extra secrets are required.

Tokens are valid for 120 seconds — long enough for the browser to consume
one and open a WebSocket, but short enough to limit replay window.
"""

from __future__ import annotations

import base64
import json
import time

from lauren import Scope, injectable

from app.crypto.crypto_service import CryptoService

_TOKEN_TTL_SECONDS = 120


@injectable(scope=Scope.SINGLETON)
class WsTokenService:
    """Creates and verifies short-lived WebSocket authentication tokens."""

    def __init__(self, crypto: CryptoService) -> None:
        self._crypto = crypto

    def create_token(self, user_id: str) -> str:
        """Return a signed token embedding *user_id* and an expiry timestamp."""
        payload = json.dumps(
            {"uid": user_id, "exp": int(time.time()) + _TOKEN_TTL_SECONDS},
            separators=(",", ":"),
        ).encode()
        payload_b64 = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
        sig = self._crypto.sign(payload_b64.encode())
        return f"{payload_b64}.{sig}"

    def verify_token(self, token: str) -> str | None:
        """Return the user_id if the token is valid and not expired, else ``None``."""
        try:
            payload_b64, sig = token.rsplit(".", 1)
        except ValueError:
            return None
        if not self._crypto.verify(payload_b64.encode(), sig):
            return None
        try:
            # Restore padding stripped during creation
            padding = 4 - len(payload_b64) % 4
            padded = payload_b64 + ("=" * (padding % 4))
            payload = json.loads(base64.urlsafe_b64decode(padded))
            if int(payload["exp"]) < int(time.time()):
                return None
            return str(payload["uid"])
        except Exception:
            return None
