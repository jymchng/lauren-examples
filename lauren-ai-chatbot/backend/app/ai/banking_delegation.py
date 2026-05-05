# NOTE: Do NOT add `from __future__ import annotations` to this file.
# The @tool() decorator uses inspect.signature() at decoration time to build
# the JSON schema, and PEP 563 lazy evaluation breaks that introspection.
"""DelegateToBankingTransfer — CRM tool that routes transfer tasks to the Transfer Agent.

``TransferAgentRunner`` is a dedicated runner subclass used as a distinct DI
token for the Transfer Agent's runner.  This breaks the circular dependency:

  AgentRunner (CRM) → DelegateToBankingTransfer → TransferAgentRunner

Because the two runner tokens are distinct the DI container can resolve
``TransferAgentRunner`` independently of ``AgentRunner`` — no cycle.

Security
--------
The authenticated identity is read from ``ctx.execution_context`` (set
server-side by the HTTP controller) and forwarded verbatim to the Transfer
Agent's runner call.  The LLM never supplies or influences the identity — it
only describes the task (recipient, amount, etc.).
"""

import logging

from lauren import injectable, Scope
from lauren_ai import AgentRunnerBase, ToolContext, tool

from app.ai.transfer_agent import BankingTransferAgent


logger = logging.getLogger(__name__)


@injectable(scope=Scope.SINGLETON)
class TransferAgentRunner(AgentRunnerBase):
    """Distinct DI token for the Transfer Agent's runner.

    Passed via ``injects=[TransferAgentRunner]`` to ``AgentModule.for_root()``
    so that ``DelegateToBankingTransfer`` can inject it by concrete type,
    avoiding ambiguity with the CRM ``AgentRunner``.
    """

@injectable(scope=Scope.SINGLETON)
class CRMAgentRunner(AgentRunnerBase):
    """Distinct DI token for the CRM Agent's runner.

    Passed via ``injects=[CRMAgentRunner]`` to ``AgentModule.for_root()``
    so that ``BankingChatController`` can inject the CRM runner by concrete type.
    """


@tool()
class DelegateToBankingTransfer:
    """Delegate a banking transfer task to the Transfer Agent.

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
        transfer_agent: BankingTransferAgent,
        runner: TransferAgentRunner,     # was: AgentRunner (Protocol) — ambiguous
    ) -> None:
        self._transfer_agent = transfer_agent
        self._runner = runner


    async def run(self, ctx: ToolContext, task: str) -> dict:
        logger.debug("DelegateToBankingTransfer.run: task_len=%d", len(task))
        # Forward the server-side execution context intact so that the
        # Transfer Agent's TransferFundsTool can read
        # ctx.execution_context["user_id"] without relying on the LLM.
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
