"""ApprovalService — manages pending human-in-the-loop transfer approvals.

Each approval is identified by a UUID4 approval_id.  The agent calls
``create()`` to register a pending approval and receives an asyncio.Future;
it then awaits that future (with a timeout).  The browser calls
``resolve()`` (via the ApprovalController) to complete the future and unblock
the agent.

Cross-user protection: ``resolve()`` checks that the caller's user_id matches
the one stored at ``create()`` time, preventing approval forgery.
"""

from __future__ import annotations

import asyncio

from lauren import Scope, injectable


@injectable(scope=Scope.SINGLETON)
class ApprovalService:
    """Singleton that stores pending approval futures and resolves them."""

    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[bool]] = {}
        self._meta: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        approval_id: str,
        user_id: str,
        details: dict,
    ) -> asyncio.Future[bool]:
        """Register a new pending approval and return the associated Future."""
        loop = asyncio.get_event_loop()
        fut: asyncio.Future[bool] = loop.create_future()
        async with self._lock:
            self._pending[approval_id] = fut
            self._meta[approval_id] = {"user_id": user_id, **details}
        return fut

    async def resolve(
        self,
        approval_id: str,
        user_id: str,
        approved: bool,
    ) -> bool:
        """Resolve a pending approval.

        Returns ``False`` when the approval_id is unknown, already consumed,
        or the user_id does not match the one that created the request.
        """
        async with self._lock:
            meta = self._meta.get(approval_id)
            fut = self._pending.get(approval_id)

        if fut is None or meta is None:
            return False
        if meta["user_id"] != user_id:
            return False
        # Results in a no-op if the future is already done (e.g. due to timeout or prior resolution),
        # ensuring idempotence and preventing cross-user forgery.
        # The agent will see the same result regardless of whether the approval was resolved before or after the timeout, preventing
        # race conditions.
        if fut.done():
            return False
        if not fut.done():
            fut.set_result(approved)
        async with self._lock:
            self._pending.pop(approval_id, None)
            self._meta.pop(approval_id, None)
        return True
