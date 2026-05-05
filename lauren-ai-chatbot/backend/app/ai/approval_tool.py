"""ApprovalTool — HITL gate that pauses the transfer agent until the user approves.

Flow
----
1. Extract the authenticated ``auth_uid`` and ``conversation_id`` from context.
2. Generate a UUID4 ``approval_id`` and register a pending asyncio.Future with
   ``ApprovalService``.
3. Push a ``transfer_approval_request`` WebSocket event to the authenticated
   user's browser connections via ``EventForwarder``.
4. ``asyncio.wait_for(asyncio.shield(fut), timeout=120)`` blocks the agent turn
   while the SSE keep_alive (15 s) holds the HTTP connection open.
5. On approval: write a signed one-shot token into
   ``ctx.agent_context.metadata["transfer_approved"]``.  ``TransferFundsTool``
   validates and consumes it before executing any transfer.
6. On rejection or timeout: return ``{"approved": False}``.
"""

from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from lauren_ai import ToolContext, tool

from app.ai.approval_service import ApprovalService
from app.ws.event_forwarder import EventForwarder


def _auth_uid(ctx: ToolContext) -> str:
    """Extract the guard-verified user_id — same helper as banking_tools.py."""
    exec_ctx = ctx.execution_context
    if exec_ctx is None:
        return ""
    request = getattr(exec_ctx, "request", None)
    if request is None:
        return ""
    state = getattr(request, "state", None)
    if state is None:
        return ""
    return (state.get("user_id") or "").lower()


@tool()
class ApprovalTool:
    """Request explicit human approval before a bank transfer is executed.

    Always call this tool FIRST with the exact transfer details before calling
    ``TransferFundsTool``.  The tool blocks until the user approves or declines
    via the browser dialog (120 s timeout).

    Args:
        to_user: Recipient user ID (alice, bob, or charlie).
        amount: Transfer amount in USD (must be positive).
        description: Optional memo shown to the user in the approval dialog.
    """

    def __init__(
        self,
        approval_svc: ApprovalService,
        forwarder: EventForwarder,
    ) -> None:
        self._approval_svc = approval_svc
        self._forwarder = forwarder

    async def run(
        self,
        ctx: ToolContext,
        to_user: str,
        amount: float,
        description: str = "",
    ) -> dict:
        auth_uid = _auth_uid(ctx)
        if not auth_uid:
            return {
                "error": ("Security error: no authenticated user found in ExecutionContext.  Cannot request approval.")
            }

        conversation_id: str = ""
        if ctx.agent_context is not None:
            conversation_id = ctx.agent_context.metadata.get("conversation_id", "") or ""

        approval_id = str(uuid4())

        fut = await self._approval_svc.create(
            approval_id,
            auth_uid,
            {"to_user": to_user, "amount": amount, "description": description},
        )

        await self._forwarder.send_to_user(
            auth_uid,
            {
                "type": "transfer_approval_request",
                "approval_id": approval_id,
                "from_user": auth_uid,
                "to_user": to_user,
                "amount_usd": amount,
                "description": description,
                "conversation_id": conversation_id,
            },
        )

        try:
            approved = await asyncio.wait_for(asyncio.shield(fut), timeout=120.0)
        except asyncio.TimeoutError:
            return {"approved": False, "reason": "approval_timeout"}

        if approved:
            if ctx.agent_context is not None:
                ctx.agent_context.metadata["transfer_approved"] = {
                    "approved": True,
                    "approval_id": approval_id,
                    "conversation_id": conversation_id,
                    "to_user": to_user,
                    "amount": amount,
                    "approved_at": time.time(),
                }
            return {"approved": True, "message": "User approved the transfer."}

        return {"approved": False, "reason": "user_declined"}
