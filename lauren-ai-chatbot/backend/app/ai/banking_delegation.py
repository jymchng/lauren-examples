"""DelegateToBankingTransfer — CRM tool that routes transfer tasks to the Transfer Agent.

Mirrors the DelegateToResearcher / DelegateToCodeAssistant pattern:
the tool is a class-form injectable; BankingDelegationWiring (a singleton)
sets the AgentRunner reference after the DI container is fully built, avoiding
a circular dependency at construction time.

Security
--------
The authenticated identity is read from ``ctx.execution_context`` (set
server-side by the HTTP controller) and forwarded verbatim to the Transfer
Agent's runner call.  The LLM never supplies or influences the identity — it
only describes the task (recipient, amount, etc.).

``from __future__ import annotations`` is kept intentionally: the
``runner: AgentRunner | None = None`` constructor annotation must remain a
forward-reference string so the DI container's ForwardRef resolution yields
no registered provider, keeping ``runner`` at its default ``None`` and
breaking the AgentRunner → ToolRegistry → tool → AgentRunner circular dep.
"""

from __future__ import annotations

import logging

from lauren import injectable
from lauren.types import Scope
from lauren_ai import AgentRunner, ToolContext, tool

from app.ai.transfer_agent import BankingTransferAgent

logger = logging.getLogger(__name__)


@tool()
class DelegateToBankingTransfer:
    """Delegate a banking transfer or account-operation task to the Transfer Agent.

    Use this for any request involving:
    - Transferring funds between accounts
    - Detailed transaction history
    - Any operation that modifies account balances

    The authenticated user is derived automatically from the session context;
    you only need to describe what should be done.

    Args:
        task: Full description of what the Transfer Agent should do.
              Include amount, recipient, and any relevant context.
    """

    def __init__(
        self,
        transfer_agent: BankingTransferAgent,
        runner: AgentRunner | None = None,
    ) -> None:
        self._transfer_agent = transfer_agent
        self._runner: AgentRunner | None = runner

    async def run(self, ctx: ToolContext, task: str) -> dict:
        logger.debug(
            "DelegateToBankingTransfer.run: task_len=%d runner_wired=%s",
            len(task),
            self._runner is not None,
        )
        if not self._runner:
            logger.debug("DelegateToBankingTransfer.run: runner not wired")
            return {"error": "Transfer service is temporarily unavailable."}

        # Forward the server-side execution context intact so that the
        # Transfer Agent's tools (TransferFundsTool, GetTransactionHistoryTool)
        # can read ctx.execution_context["user_id"] without relying on the LLM.
        response = await self._runner.run(
            self._transfer_agent,
            task,
            execution_context=ctx.execution_context,
        )
        logger.debug(
            "DelegateToBankingTransfer.run: completed turns=%d stop=%s",
            response.turns,
            response.stop_reason,
        )
        return {"result": response.content, "stop_reason": response.stop_reason}


@injectable(scope=Scope.SINGLETON)
class BankingDelegationWiring:
    """Post-DI singleton that wires the AgentRunner into DelegateToBankingTransfer.

    Without this, the tool is constructed before the AgentRunner exists, so
    ``runner`` defaults to ``None``.  This wiring singleton receives both the
    fully-built runner and the tool instance, then sets the runner reference.
    """

    def __init__(
        self,
        runner: AgentRunner,
        delegation_tool: DelegateToBankingTransfer,
    ) -> None:
        delegation_tool._runner = runner
        logger.debug("BankingDelegationWiring: AgentRunner wired into DelegateToBankingTransfer")
