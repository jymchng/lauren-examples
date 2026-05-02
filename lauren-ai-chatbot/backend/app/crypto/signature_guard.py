"""SignatureGuard — verifies that every chat request has a signed payload.

How it works
------------
1. Reads the ``X-Signature`` header from the request.
2. Reads the raw request body (Lauren caches the first read so downstream
   extractors — e.g. ``Json[ChatRequest]`` — can still consume it).
3. Asks ``CryptoService.verify`` whether the body matches the signature.
4. Returns ``True`` on success; raises ``UnauthorizedError`` otherwise.

The guard is declared as a SINGLETON injectable: ``CryptoService`` is
injected via the constructor, matching the NestJS-style guard pattern that
Lauren supports.

Placement
---------
Applied at the controller level via ``@use_guards(SignatureGuard)`` so every
route in ``ChatController`` is automatically protected::

    @use_guards(SignatureGuard)
    @controller("/api/chat")
    class ChatController: ...
"""

from lauren import Scope, injectable
from lauren.exceptions import UnauthorizedError
from lauren.types import ExecutionContext

from app.crypto.crypto_service import CryptoService


@injectable(scope=Scope.SINGLETON)
class SignatureGuard:
    """Guard that rejects requests with a missing or invalid payload signature."""

    def __init__(self, crypto: CryptoService) -> None:
        self._crypto = crypto

    async def can_activate(self, ctx: ExecutionContext) -> bool:
        signature = ctx.request.headers.get("x-signature")
        if not signature:
            raise UnauthorizedError(
                "Missing X-Signature header — requests must be signed by the frontend"
            )

        body = await ctx.request.body()
        if not self._crypto.verify(body, signature):
            raise UnauthorizedError("Invalid payload signature")

        return True
