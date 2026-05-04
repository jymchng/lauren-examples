"""SignatureGuard — verifies every chat request has a valid signed payload,
then pins the authenticated user identity to ``request.state``.

How it works
------------
1. Reads the ``X-Signature`` header from the request.
2. Reads the raw request body (Lauren caches the first read so downstream
   extractors — e.g. ``Json[ChatRequest]`` — can still consume it).
3. Asks ``CryptoService.verify`` whether the body matches the signature.
4. On success, parses ``user_id`` from the verified JSON body and stores it
   on ``ctx.request.state.user_id`` so all downstream code (controller,
   agent tools) can read the *cryptographically anchored* identity from the
   request state rather than trusting a user-supplied string.

Security note
-------------
Because the body is HMAC-signed by the frontend with a server-held secret,
any ``user_id`` inside a verified body is tamper-proof.  Downstream code
**must** read identity from ``request.state.user_id`` set here, never from
raw request body fields or from LLM-supplied tool parameters.

Placement
---------
Applied at the controller level via ``@use_guards(SignatureGuard)`` so every
route in the controller is automatically protected::

    @use_guards(SignatureGuard)
    @controller("/api/banking")
    class BankingChatController: ...
"""

import json as _json

from lauren import Scope, injectable
from lauren.exceptions import UnauthorizedError
from lauren.types import ExecutionContext

from app.crypto.crypto_service import CryptoService


@injectable(scope=Scope.SINGLETON)
class SignatureGuard:
    """Guard that verifies the payload signature and pins ``user_id`` to request state."""

    def __init__(self, crypto: CryptoService) -> None:
        self._crypto = crypto

    async def can_activate(self, ctx: ExecutionContext) -> bool:
        signature = ctx.request.headers.get("x-signature")
        if not signature:
            raise UnauthorizedError("Missing X-Signature header — requests must be signed by the frontend")

        body_bytes = await ctx.request.body()
        if not self._crypto.verify(body_bytes, signature):
            raise UnauthorizedError("Invalid payload signature")

        # Body is HMAC-verified — the user_id inside it cannot have been tampered
        # with by the browser.  Pin it to request.state so the controller and
        # every tool downstream reads identity from here, not from free text.
        try:
            payload = _json.loads(body_bytes)
            user_id = str(payload.get("user_id", "")).strip().lower()
            if user_id:
                ctx.request.state.user_id = user_id
        except (ValueError, KeyError):
            pass  # Malformed JSON — controller will reject the unknown user

        return True
