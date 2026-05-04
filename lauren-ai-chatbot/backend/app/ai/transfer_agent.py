"""BankingTransferAgent — back-office agent that executes fund transfers.

This agent is NOT directly accessible from the chat interface. It is only
reachable via the DelegateToBankingTransfer tool used by the CRM Agent.

Security contract
-----------------
Authentication is enforced at the tool layer via ToolContext.execution_context,
not via LLM-supplied parameters. TransferFundsTool and GetTransactionHistoryTool
read ctx.execution_context["user_id"] (set server-side by the HTTP controller)
and ignore any identity the LLM might otherwise supply. This agent only needs
to describe what to do (recipient, amount) — not who is authorising it.
"""

from __future__ import annotations

import logging
import time

from lauren_ai import AgentContext, AgentResponse, Completion, ToolResult, agent, use_tools

from app.ai.banking_tools import TransferFundsTool

_SYSTEM = """\
You are the SecureBank Transfer Agent — a back-office system that executes \
fund transfers for verified customers.

══ CAPABILITIES ══════════════════════════════════════════════════════════════
• TransferFundsTool  — transfer funds (to_user, amount, optional description)

The sender identity is determined automatically from the verified session — \
you do not need to supply or verify it yourself.

After every successful transfer, state the transaction ID, updated balance, and \
recipient name clearly.
"""

logger = logging.getLogger(__name__)


@agent(model=None, system=_SYSTEM, max_turns=5)
@use_tools(TransferFundsTool)
class BankingTransferAgent:
    """Back-office transfer execution agent (reached only via CRM delegation)."""

    async def on_start(self, ctx: AgentContext) -> None:
        ctx.metadata["_start"] = time.monotonic()
        logger.debug("BankingTransferAgent.on_start: turn=%d", ctx.turn)

    async def on_turn_complete(self, completion: Completion, ctx: AgentContext) -> None:
        # Avoid logging content — may contain transaction details.
        logger.debug("BankingTransferAgent.on_turn_complete: turn=%d", ctx.turn)

    async def on_tool_result(self, result: ToolResult, ctx: AgentContext) -> ToolResult | None:
        if result.is_error:
            logger.debug("BankingTransferAgent.on_tool_result: id=%s ERROR", result.tool_use_id)
        else:
            logger.debug("BankingTransferAgent.on_tool_result: id=%s ok", result.tool_use_id)
        return None

    async def on_finish(self, response: AgentResponse, ctx: AgentContext) -> None:
        elapsed = time.monotonic() - ctx.metadata.get("_start", time.monotonic())
        logger.debug(
            "BankingTransferAgent.on_finish: turns=%d stop=%s elapsed=%.3fs",
            response.turns,
            response.stop_reason,
            elapsed,
        )
