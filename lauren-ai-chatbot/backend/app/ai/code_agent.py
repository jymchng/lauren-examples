"""CodeAssistantAgent — executes Python and analyses results for the orchestrator."""

from __future__ import annotations

import logging
import time

from lauren_ai import (
    AgentContext,
    AgentResponse,
    Completion,
    LengthFilter,
    PromptInjectionFilter,
    ToolResult,
    agent,
    use_guardrails,
    use_tools,
)
from lauren_ai._skills import CodeExecutionTool

from app.ai.tools import calculate, word_count

logger = logging.getLogger(__name__)


@agent(
    model="poolside/laguna-xs.2:free",
    system=(
        "You are a code assistant. "
        "Execute Python snippets and analyse the results. "
        "Always show the code you ran and explain the output."
    ),
)
@use_guardrails(
    input=[PromptInjectionFilter()],
    output=[LengthFilter(max_chars=6000)],
)
@use_tools(CodeExecutionTool, calculate, word_count)
class CodeAssistantAgent:
    """Specialist agent for code execution and mathematical analysis.

    Protected by:
    - Input: ``PromptInjectionFilter`` — blocks jailbreak attempts.
    - Output: ``LengthFilter`` — caps responses at 6 000 characters.
    """

    async def on_start(self, ctx: AgentContext) -> None:
        ctx.metadata["_start"] = time.monotonic()
        logger.debug("CodeAssistantAgent.on_start: turn=%d", ctx.turn)

    async def on_turn_complete(self, completion: Completion, ctx: AgentContext) -> None:
        logger.debug(
            "CodeAssistantAgent.on_turn_complete: turn=%d content_len=%d",
            ctx.turn,
            len(completion.content or ""),
        )

    async def on_tool_result(self, result: ToolResult, ctx: AgentContext) -> ToolResult | None:
        if result.is_error:
            logger.debug("CodeAssistantAgent.on_tool_result: id=%s ERROR: %s", result.tool_use_id, result.content)
        else:
            logger.debug("CodeAssistantAgent.on_tool_result: id=%s ok len=%d", result.tool_use_id, len(str(result.content)))
        return None

    async def on_finish(self, response: AgentResponse, ctx: AgentContext) -> None:
        elapsed = time.monotonic() - ctx.metadata.get("_start", time.monotonic())
        logger.debug(
            "CodeAssistantAgent.on_finish: turns=%d stop=%s elapsed=%.3fs",
            response.turns,
            response.stop_reason,
            elapsed,
        )
