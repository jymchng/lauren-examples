"""AuthenticatedUserGuard — rejects requests where no user_id was pinned to request.state.

Works in tandem with ``SignatureGuard``: the latter verifies the HMAC signature
and pins ``request.state.user_id`` from the verified body.  This guard then
enforces that the pin is non-empty, so route handlers can rely on a valid
authenticated user being present.

Apply at the method level to protect specific routes within a controller that
already carries ``@use_guards(SignatureGuard)``::

    @use_guards(AuthenticatedUserGuard)
    @post("/chat")
    async def stream(self, body: Json[ChatRequest], ...) -> EventStream: ...
"""

from __future__ import annotations

from lauren import Scope, injectable
from lauren.exceptions import UnauthorizedError
from lauren.types import ExecutionContext


@injectable(scope=Scope.SINGLETON)
class AuthenticatedUserGuard:
    """Rejects requests where SignatureGuard did not pin a non-empty user_id."""

    async def can_activate(self, ctx: ExecutionContext) -> bool:
        uid = ctx.request.state.get("user_id")
        if not uid:
            raise UnauthorizedError("Authentication required — please log in first")
        return True
