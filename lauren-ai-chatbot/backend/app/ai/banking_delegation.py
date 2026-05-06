# NOTE: Do NOT add `from __future__ import annotations` to this file.
# The @tool() decorator uses inspect.signature() at decoration time to build
# the JSON schema, and PEP 563 lazy evaluation breaks that introspection.
"""DelegateToBankingTransfer — CRM tool that routes transfer tasks to the Transfer Agent.

Each language pair has its own runner subclass as a distinct DI token so the
DI container can resolve them independently:

  AgentRunner (CRM EN) → DelegateToBankingTransfer → TransferAgentRunnerEN
  AgentRunner (CRM ZH) → DelegateToBankingTransfer → TransferAgentRunnerZH

Security
--------
The authenticated identity is read from ``ctx.execution_context`` (set
server-side by the HTTP controller) and forwarded verbatim to the Transfer
Agent's runner call.
"""

import logging

from lauren import injectable, Scope
from lauren_ai import AgentRunnerBase, ToolContext, tool

from app.ai.transfer_agent import BankingTransferAgentEN


logger = logging.getLogger(__name__)


@injectable(scope=Scope.SINGLETON)
class TransferAgentRunnerEN(AgentRunnerBase):
    """Distinct DI token for the English Transfer Agent's runner."""


@injectable(scope=Scope.SINGLETON)
class TransferAgentRunnerZH(AgentRunnerBase):
    """Distinct DI token for the Mandarin Transfer Agent's runner."""


@injectable(scope=Scope.SINGLETON)
class CRMAgentRunnerEN(AgentRunnerBase):
    """Distinct DI token for the English CRM Agent's runner."""


@injectable(scope=Scope.SINGLETON)
class CRMAgentRunnerZH(AgentRunnerBase):
    """Distinct DI token for the Mandarin CRM Agent's runner."""


# Backward-compatible aliases.
TransferAgentRunner = TransferAgentRunnerEN
CRMAgentRunner = CRMAgentRunnerEN


@tool()
class DelegateToBankingTransfer:
    """Delegate a banking transfer task to the English Transfer Agent.

    Use this for any request involving:
    - Transferring funds between accounts
    - Any operation that modifies account balances

    The authenticated user is derived automatically from the session context;
    you only need to describe what should be done.

    Args:
        task: Full description of what the Transfer Agent should do.
              Include amount, recipient, and any relevant context.
    """

    def __init__(
        self,
        transfer_agent: BankingTransferAgentEN,
        runner: TransferAgentRunnerEN,
    ) -> None:
        self._transfer_agent = transfer_agent
        self._runner = runner

    async def run(self, ctx: ToolContext, task: str) -> dict:
        logger.debug("DelegateToBankingTransfer.run: task_len=%d", len(task))
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
