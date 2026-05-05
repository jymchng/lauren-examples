# NOTE: Do NOT add `from __future__ import annotations` to this file.
# The @tool() decorator uses inspect.signature() at decoration time to build
# the JSON schema, and PEP 563 lazy evaluation breaks that introspection.
"""Conversation handoff tools for agent-to-agent session transfer.

These tools allow one agent to transfer the *entire conversation* to another
agent so the second agent can have multi-turn back-and-forth with the user.
This is distinct from ``DelegateToBankingTransfer``, which runs the Transfer
Agent as a one-shot subtask and returns the result to the CRM Agent.

Flow (CRM → Transfer):
  1. CRM calls ``HandoffToBankingTransfer(reason="...")``
  2. Tool sets ``active_agent = TRANSFER_AGENT_NAME`` in ``ActiveAgentStore``
  3. Tool emits ``agent_handoff`` WebSocket event so the frontend can update
     the active-agent indicator
  4. CRM ends its current turn with a graceful closing remark
  5. Next user message is routed directly to ``BankingTransferAgent`` by the
     controller (reads ``ActiveAgentStore``)

Return flow (Transfer → CRM):
  1. Transfer Agent calls ``HandoffBackToCRM(summary="...")``
  2. Tool resets ``ActiveAgentStore`` for this conversation
  3. Tool emits a reverse ``agent_handoff`` WebSocket event
  4. Subsequent messages are again routed to ``BankingCRMAgent``

Security:
  ``execution_context`` is forwarded intact through both agent runners, so the
  authenticated ``user_id`` (pinned by ``SignatureGuard``) never changes across
  the handoff boundary.
"""

import logging

from lauren_ai import ToolContext, tool

from app.ai.active_agent_store import ActiveAgentStore
from app.ai.agent_names import CRM_AGENT_NAME, TRANSFER_AGENT_NAME
from app.ws.context import current_user_id
from app.ws.event_forwarder import EventForwarder

logger = logging.getLogger(__name__)


@tool()
class HandoffToBankingTransfer:
    """Hand the active conversation to the Banking Transfer Agent.

    Unlike DelegateToBankingTransfer (one-shot subtask), this makes the
    Transfer Agent the primary conversationalist for all subsequent messages
    in this session.  The Transfer Agent can gather details, request approval,
    execute the transfer, and then call HandoffBackToCRM when done.

    Call this when the customer wants multi-step transfer assistance rather
    than a simple single-shot delegation.

    Args:
        reason: Brief explanation of why the handoff is needed (shown in the
                frontend activity feed).
    """

    def __init__(
        self,
        active_agent_store: ActiveAgentStore,
        event_forwarder: EventForwarder,
    ) -> None:
        self._store = active_agent_store
        self._forwarder = event_forwarder

    async def run(self, ctx: ToolContext, reason: str) -> dict:
        conversation_id: str = ctx.agent_context.metadata.get("conversation_id", "")
        from_name: str = ctx.agent_context.agent_name
        user_id: str | None = current_user_id.get()

        if conversation_id:
            self._store.set(conversation_id, TRANSFER_AGENT_NAME)

        if user_id:
            await self._forwarder.send_to_user(
                user_id,
                {
                    "type": "agent_handoff",
                    "from_agent": from_name,
                    "to_agent": TRANSFER_AGENT_NAME,
                    "reason": reason,
                },
            )

        logger.debug(
            "HandoffToBankingTransfer.run: conv_id=%s reason=%r",
            conversation_id,
            reason,
        )
        return {
            "status": "handed_off",
            "to_agent": TRANSFER_AGENT_NAME,
        }


@tool()
class HandoffBackToCRM:
    """Return the active conversation to the Banking CRM Agent.

    Call this after the transfer workflow is complete or when the customer
    needs assistance outside the scope of fund transfers.

    Args:
        summary: Brief description of what was accomplished (e.g. transfer
                 amount and recipient) shown in the frontend activity feed.
    """

    def __init__(
        self,
        active_agent_store: ActiveAgentStore,
        event_forwarder: EventForwarder,
    ) -> None:
        self._store = active_agent_store
        self._forwarder = event_forwarder

    async def run(self, ctx: ToolContext, summary: str) -> dict:
        conversation_id: str = ctx.agent_context.metadata.get("conversation_id", "")
        from_name: str = ctx.agent_context.agent_name
        user_id: str | None = current_user_id.get()

        if conversation_id:
            self._store.reset(conversation_id)

        if user_id:
            await self._forwarder.send_to_user(
                user_id,
                {
                    "type": "agent_handoff",
                    "from_agent": from_name,
                    "to_agent": CRM_AGENT_NAME,
                    "summary": summary,
                },
            )

        logger.debug(
            "HandoffBackToCRM.run: conv_id=%s summary=%r",
            conversation_id,
            summary,
        )
        return {
            "status": "handed_back",
            "to_agent": CRM_AGENT_NAME,
            "summary": summary,
        }
