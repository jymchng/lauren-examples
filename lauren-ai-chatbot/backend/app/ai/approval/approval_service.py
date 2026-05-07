"""ApprovalService — manages pending human-in-the-loop transfer approvals.

Each approval is identified by a UUID4 approval_id.  The agent calls
``create()`` to register a pending approval and receives an asyncio.Future;
it then awaits that future (with a timeout).  The browser calls
``resolve()`` (via the ApprovalController) to complete the future and unblock
the agent.

Cross-user protection: ``resolve()`` checks that the caller's user_id matches
the one stored at ``create()`` time, preventing approval forgery.

SSE-close cleanup: each approval is tagged with the originating
``conversation_id``.  When the SSE stream that issued it disconnects, the
controller calls ``cancel_for_conversation()`` to resolve every matching
future as ``approved=False`` so a refresh / WS-reconnect can't surface a
zombie approval prompt for a request the user already abandoned.
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
        conversation_id: str = "",
    ) -> asyncio.Future[bool]:
        """Register a new pending approval and return the associated Future.

        ``conversation_id`` is used by ``cancel_for_conversation`` to tear
        down approvals when their originating SSE stream closes.
        """
        loop = asyncio.get_event_loop()
        fut: asyncio.Future[bool] = loop.create_future()
        async with self._lock:
            self._pending[approval_id] = fut
            self._meta[approval_id] = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                **details,
            }
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

    async def cancel_for_conversation(self, conversation_id: str) -> int:
        """Cancel every pending approval tagged with *conversation_id*.

        Resolves each matching future with ``approved=False`` and removes
        it from the registry.  Called from the chat controller's SSE
        ``finally`` block so a refresh / disconnect doesn't leave zombie
        approvals that pop up on a reconnected WebSocket.

        Returns the number of approvals cancelled (useful for tests / logs).
        """
        if not conversation_id:
            return 0
        async with self._lock:
            stale = [aid for aid, meta in self._meta.items() if meta.get("conversation_id") == conversation_id]
            cancelled = 0
            for aid in stale:
                fut = self._pending.pop(aid, None)
                self._meta.pop(aid, None)
                if fut is not None and not fut.done():
                    fut.set_result(False)
                    cancelled += 1
        return cancelled
