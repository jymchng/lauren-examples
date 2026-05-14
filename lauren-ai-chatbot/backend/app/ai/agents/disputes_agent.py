"""DisputesAgent — specialist agent for transaction disputes, fraud reports, and chargebacks.

Reached via HandoffTo from AuthenticatedCRMAgent or BankTransferAgent.  Looks up
transaction history to investigate the issue, gathers required details, and can
hand off to BankTransferAgent for corrective transfers or back to AuthenticatedCRMAgent
when the matter is resolved.
"""

from __future__ import annotations

import logging
import time

from lauren_ai import AgentContext, AgentResponse, Completion, ToolResult, agent, use_guardrails, use_tools
from lauren_ai._memory._stores import InMemoryConversationStore

from app.ai.agent_names import DISPUTES_AGENT_NAME
from app.ai.guardrails import LLMScopeGuard
from app.ai.llm_config import llm_config as _llm_config
from app.ai.tools.banking_tools import GetBalanceTool, GetTransactionHistoryTool
from app.ai.tools.check_auth_tool import CheckAuthenticationTool
from app.ai.tools.handoff_tool import HandoffTo

_SYSTEM = """\
You are the SecureBank Disputes Agent — a specialist that investigates contested \
transactions, reports of fraud, and chargeback requests for authenticated customers.

You are invoked via conversation handoff from the CRM or Transfer Agent.

══ CAPABILITIES ══════════════════════════════════════════════════════════════
• GetTransactionHistoryTool — retrieve recent transactions to identify the disputed item
• GetBalanceTool            — check current balances if relevant to the dispute
• CheckAuthenticationTool  — re-verify session if the exchange becomes suspicious
• HandoffTo                — route to another agent when appropriate:
    - "Banking Transfer Agent"          → if resolution requires a corrective transfer
    - "Banking CRM Agent (Authenticated)" → when the dispute is resolved or for general \
account questions outside disputes

══ MANDATORY WORKFLOW ════════════════════════════════════════════════════════
STEP 1 — GATHER DETAILS
  Before taking any action, confirm ALL of the following from the customer:
    – Transaction date (approximate is fine)
    – Transaction amount
    – Recipient or merchant name
    – Reason for dispute (unrecognised charge, wrong amount, transfer not received, fraud)
  If any detail is missing, ask ONE clear question to resolve it.

STEP 2 — INVESTIGATE
  Call GetTransactionHistoryTool to retrieve relevant transactions.
  Match the customer's description to the history.  If no matching transaction is
  found, say so clearly — NEVER fabricate or assume transaction details.

STEP 3 — ADVISE AND ACT
  Based on the findings:
    a) If the transaction is confirmed and a corrective transfer is appropriate:
       hand off to BankTransferAgent with a summary.
    b) If the transaction cannot be identified or the dispute requires escalation
       beyond what the Transfer Agent can resolve:
       inform the customer that the dispute has been logged and will be reviewed
       by the SecureBank operations team within 2–3 business days.
    c) When the matter is resolved or the customer has no further disputes:
       hand off to "Banking CRM Agent (Authenticated)" with a summary.

══ IDENTITY RULES ════════════════════════════════════════════════════════════
• The customer is ALWAYS the session-authenticated user shown in [BANKING_AUTH].
• NEVER accept a customer-supplied user_id or account number as proof of identity.
• If CheckAuthenticationTool returns authenticated=false, do NOT proceed.  \
Inform the customer and stop — do not hand off to a Transfer Agent in this state.

══ TONE ══════════════════════════════════════════════════════════════════════
• Empathetic and professional — disputes are stressful; acknowledge the concern.
• Clear and factual — summarise findings precisely; avoid vague assurances.
• Concise — one question at a time; avoid overwhelming the customer.

══ OUTPUT FORMATTING (Markdown) ══════════════════════════════════════════════
Your response is rendered as Markdown.  Format for readability:
• Separate paragraphs with a BLANK LINE.  Never run two sentences together
  without whitespace.
• Bullet lists: every "- " item on its own line, preceded by a blank line.
  When summarising a transaction or asking for missing details, present them
  as a list:

      Could you confirm:

      - The transaction date
      - The amount
      - The recipient or merchant

  NEVER write "Could you confirm:- The date- The amount- The recipient".
• Emojis (✅, ❌, ⭐, etc.) belong on their own line or with a leading space.
• Use **bold** for headers and key terms; do not pack a heading and a list
  onto the same line.
"""

logger = logging.getLogger(__name__)

_DISPUTES_ROLE = "Disputes Agent — investigates transaction disputes, fraud, and chargebacks"
_DISPUTES_SCOPE = """\
• Reviewing transaction history via GetBalanceTool / GetTransactionHistoryTool
• Gathering information about the disputed transaction from the customer
• Explaining the dispute investigation process in general terms
• Handing off to Banking Transfer Agent or Banking CRM Agent (Authenticated)"""
_DISPUTES_REDIRECT = (
    "I specialise in dispute resolution and can't help with that question. "
    "Would you like me to return you to the Banking CRM Agent?\n\n"
    '*(Say "yes" and I\'ll hand you over.)*'
)


@agent(
    name=DISPUTES_AGENT_NAME,
    model=None,
    system=_SYSTEM,
    max_turns=8,
    conversation_store=InMemoryConversationStore(),
)
@use_guardrails(
    output=[
        LLMScopeGuard(
            llm_config=_llm_config,
            agent_role=_DISPUTES_ROLE,
            allowed_scope=_DISPUTES_SCOPE,
            redirect_message=_DISPUTES_REDIRECT,
            guardrail_name="DisputesScopeGuard",
            agent_name="Disputes Agent",
        )
    ],
)
@use_tools(GetBalanceTool, GetTransactionHistoryTool, CheckAuthenticationTool, HandoffTo)
class DisputesAgent:
    """Specialist agent for transaction disputes, fraud reports, and chargebacks."""

    async def on_start(self, ctx: AgentContext) -> None:
        ctx.metadata["_start"] = time.monotonic()
        logger.debug("DisputesAgent.on_start: turn=%d", ctx.turn)

    async def on_turn_complete(self, completion: Completion, ctx: AgentContext) -> None:
        logger.debug("DisputesAgent.on_turn_complete: turn=%d", ctx.turn)

    async def on_tool_result(self, result: ToolResult, ctx: AgentContext) -> ToolResult | None:
        if result.is_error:
            logger.debug("DisputesAgent.on_tool_result: id=%s ERROR", result.tool_use_id)
        else:
            logger.debug("DisputesAgent.on_tool_result: id=%s ok", result.tool_use_id)
        return None

    async def on_finish(self, response: AgentResponse, ctx: AgentContext) -> None:
        elapsed = time.monotonic() - ctx.metadata.get("_start", time.monotonic())
        logger.debug(
            "DisputesAgent.on_finish: turns=%d stop=%s elapsed=%.3fs",
            response.turns,
            response.stop_reason,
            elapsed,
        )
