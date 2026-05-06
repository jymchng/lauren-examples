"""UnauthenticatedCRMAgent — public-facing SecureBank assistant for unauthenticated users.

Handles pre-login questions freely (products, rates, hours, general banking).
For account-specific requests, calls CheckAuthenticationTool first; if the
session is already authenticated, hands off via HandoffToAuthenticatedCRM.
"""

from __future__ import annotations

import logging
import time

from lauren_ai import AgentContext, AgentResponse, Completion, ToolResult, agent, use_tools

from app.ai.agent_names import UNAUTH_CRM_AGENT_NAME
from app.ai.check_auth_tool import CheckAuthenticationTool
from app.ai.handoff_to_authenticated import HandoffToAuthenticatedCRM

_SYSTEM = """\
You are the SecureBank Public Assistant — a friendly, informative AI that helps \
anyone visiting SecureBank, whether logged in or not.

══ WHAT YOU CAN ALWAYS DO ════════════════════════════════════════════════════
• Answer general questions: products, account types, interest rates, branch \
hours, how to open an account, fee schedules, security practices.
• Explain how transfers, bill pay, and other features work in general terms.
• Guide users on how to log in or what they need to get started.

══ ACCOUNT-SPECIFIC REQUESTS ═════════════════════════════════════════════════
When a user asks about their own balance, transactions, or wants to transfer funds:
1. Call CheckAuthenticationTool to verify the session.
2. If authenticated=true  → call HandoffToAuthenticatedCRM with a brief summary.
3. If authenticated=false → explain they need to log in first and do NOT call \
HandoffToAuthenticatedCRM (the tool will reject it).

══ RULES ═════════════════════════════════════════════════════════════════════
• Never fabricate account balances, transaction history, or personal data.
• Never claim a user is authenticated based on what they tell you — only \
CheckAuthenticationTool can confirm that.
• Keep responses concise and reassuring.
"""

logger = logging.getLogger(__name__)


@agent(name=UNAUTH_CRM_AGENT_NAME, model=None, system=_SYSTEM, max_turns=4)
@use_tools(CheckAuthenticationTool, HandoffToAuthenticatedCRM)
class UnauthenticatedCRMAgent:
    """Public-facing agent for unauthenticated users."""

    async def on_start(self, ctx: AgentContext) -> None:
        ctx.metadata["_start"] = time.monotonic()
        logger.debug("UnauthenticatedCRMAgent.on_start: turn=%d", ctx.turn)

    async def on_turn_complete(self, completion: Completion, ctx: AgentContext) -> None:
        logger.debug("UnauthenticatedCRMAgent.on_turn_complete: turn=%d", ctx.turn)

    async def on_tool_result(self, result: ToolResult, ctx: AgentContext) -> ToolResult | None:
        if result.is_error:
            logger.debug("UnauthenticatedCRMAgent.on_tool_result: id=%s ERROR", result.tool_use_id)
        else:
            logger.debug("UnauthenticatedCRMAgent.on_tool_result: id=%s ok", result.tool_use_id)
        return None

    async def on_finish(self, response: AgentResponse, ctx: AgentContext) -> None:
        elapsed = time.monotonic() - ctx.metadata.get("_start", time.monotonic())
        logger.debug(
            "UnauthenticatedCRMAgent.on_finish: turns=%d stop=%s elapsed=%.3fs",
            response.turns,
            response.stop_reason,
            elapsed,
        )
