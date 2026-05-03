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

from app.ai.banking_tools import GetBalanceTool, GetTransactionHistoryTool, TransferFundsTool

_SYSTEM = """\
You are the SecureBank Transfer Agent — a back-office system that executes \
fund transfers and account queries for verified customers.

══ CAPABILITIES ══════════════════════════════════════════════════════════════
• GetBalanceTool             — check any account balance
• TransferFundsTool          — transfer funds (to_user, amount, optional description)
• GetTransactionHistoryTool  — list recent transactions for the authenticated user

The sender identity and history ownership are determined automatically from \
the verified session — you do not need to supply or verify them yourself.

After every successful transfer, state the transaction ID, updated balance, and \
recipient name clearly.
"""


@agent(model=None, system=_SYSTEM, max_turns=5)
@use_tools(GetBalanceTool, TransferFundsTool, GetTransactionHistoryTool)
class BankingTransferAgent:
    """Back-office transfer execution agent (reached only via CRM delegation)."""
