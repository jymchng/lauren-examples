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
from typing import Generic, TypeVar

from lauren_ai import ToolContext, tool

from app.ai.active_agent_store import ActiveAgentStore
from app.ai.agent_names import CRM_AGENT_NAME, TRANSFER_AGENT_NAME
from app.ws.context import current_user_id
from app.ws.event_forwarder import EventForwarder

logger = logging.getLogger(__name__)

_GenericAgentType = TypeVar("_GenericAgentType", bound=type)


@tool()
class HandoffBackTo(Generic[_GenericAgentType]):
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
        to_name: str = CRM_AGENT_NAME if from_name == TRANSFER_AGENT_NAME else TRANSFER_AGENT_NAME
        user_id: str = (
            ctx.execution_context.request.state.get("user_id")
            if ctx.execution_context and ctx.execution_context.request and ctx.execution_context.request.state
            else None
        ) or ""
        
        if conversation_id:
            if to_name == CRM_AGENT_NAME:
                self._store.reset(conversation_id)
            else:
                self._store.set(conversation_id, to_name)
            self._store.set_pending_summary(conversation_id, summary)

        await self._forwarder.send_to_user(
            user_id,
            {
                "type": "agent_handoff",
                "from_agent": from_name,
                "to_agent": to_name,
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
            "to_agent": to_name,
            "summary": summary,
        }
