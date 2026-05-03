"""OrchestratorAgent — top-level agent that routes to specialist sub-agents.

Architecture
------------
The orchestrator receives every user message from the /api/agent/ endpoint.
It decides which specialist to delegate to (or answers directly) based on the
nature of the request:

- Research / URL fetching   → ``DelegateToResearcher``
- Code execution / maths    → ``DelegateToCodeAssistant``
- General questions          → answers directly with its own knowledge
"""

from __future__ import annotations

import logging
import time

from lauren_ai import (
    AgentContext,
    AgentResponse,
    Completion,
    LengthFilter,
    PIIRedactor,
    PromptInjectionFilter,
    ToolResult,
    agent,
    use_guardrails,
    use_tools,
)

from app.ai.delegation_tools import DelegateToCodeAssistant, DelegateToResearcher
from app.ai.tools import get_current_time

_SYSTEM = """\
You are a helpful orchestrator assistant with access to specialist sub-agents.

When to delegate:
- Research, URL fetching, or information gathering → use delegate_to_researcher
- Python code execution, complex maths, or data analysis → use delegate_to_code_assistant
- General questions, explanations, writing help → answer directly

Always tell the user which specialist you are routing to and why.
Synthesise the specialist's result into a clear, concise final answer.
"""

logger = logging.getLogger(__name__)


@agent(model="poolside/laguna-xs.2:free", system=_SYSTEM)
@use_guardrails(
    input=[PromptInjectionFilter(), PIIRedactor()],
    output=[LengthFilter(max_chars=8000)],
)
@use_tools(DelegateToResearcher, DelegateToCodeAssistant, get_current_time)
class OrchestratorAgent:
    """Top-level routing agent with access to specialist sub-agents.

    Protected by:
    - Input: ``PromptInjectionFilter`` + ``PIIRedactor`` — blocks jailbreaks and
      redacts sensitive personal information before it reaches the model.
    - Output: ``LengthFilter`` — caps responses at 8 000 characters.
    """

    async def on_start(self, ctx: AgentContext) -> None:
        ctx.metadata["_start"] = time.monotonic()
        logger.debug("OrchestratorAgent.on_start: turn=%d", ctx.turn)

    async def on_turn_complete(self, completion: Completion, ctx: AgentContext) -> None:
        logger.debug(
            "OrchestratorAgent.on_turn_complete: turn=%d content_len=%d",
            ctx.turn,
            len(completion.content or ""),
        )

    async def on_tool_result(self, result: ToolResult, ctx: AgentContext) -> ToolResult | None:
        if result.is_error:
            logger.debug("OrchestratorAgent.on_tool_result: id=%s ERROR: %s", result.tool_use_id, result.content)
        else:
            logger.debug("OrchestratorAgent.on_tool_result: id=%s ok len=%d", result.tool_use_id, len(str(result.content)))
        return None

    async def on_finish(self, response: AgentResponse, ctx: AgentContext) -> None:
        elapsed = time.monotonic() - ctx.metadata.get("_start", time.monotonic())
        logger.debug(
            "OrchestratorAgent.on_finish: turns=%d stop=%s elapsed=%.3fs",
            response.turns,
            response.stop_reason,
            elapsed,
        )
