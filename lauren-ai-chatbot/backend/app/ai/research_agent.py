"""ResearchAgent — fetches URLs and gathers information for the orchestrator."""

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
from lauren_ai._skills import HttpFetchTool

from app.ai.tools import get_current_time

logger = logging.getLogger(__name__)


@agent(
    model="poolside/laguna-xs.2:free",
    system=(
        "You are a research assistant. "
        "Fetch pages and gather information from the web. "
        "Always cite the URLs you consulted and summarise your findings clearly."
    ),
)
@use_guardrails(
    input=[PromptInjectionFilter()],
    output=[LengthFilter(max_chars=6000)],
)
@use_tools(HttpFetchTool, get_current_time)
class ResearchAgent:
    """Specialist agent for web research and URL fetching.

    Protected by:
    - Input: ``PromptInjectionFilter`` — blocks jailbreak attempts.
    - Output: ``LengthFilter`` — caps responses at 6 000 characters.
    """

    async def on_start(self, ctx: AgentContext) -> None:
        ctx.metadata["_start"] = time.monotonic()
        logger.debug("ResearchAgent.on_start: turn=%d", ctx.turn)

    async def on_turn_complete(self, completion: Completion, ctx: AgentContext) -> None:
        logger.debug(
            "ResearchAgent.on_turn_complete: turn=%d content_len=%d",
            ctx.turn,
            len(completion.content or ""),
        )

    async def on_tool_result(self, result: ToolResult, ctx: AgentContext) -> ToolResult | None:
        if result.is_error:
            logger.debug("ResearchAgent.on_tool_result: id=%s ERROR: %s", result.tool_use_id, result.content)
        else:
            logger.debug("ResearchAgent.on_tool_result: id=%s ok len=%d", result.tool_use_id, len(str(result.content)))
        return None

    async def on_finish(self, response: AgentResponse, ctx: AgentContext) -> None:
        elapsed = time.monotonic() - ctx.metadata.get("_start", time.monotonic())
        logger.debug(
            "ResearchAgent.on_finish: turns=%d stop=%s elapsed=%.3fs",
            response.turns,
            response.stop_reason,
            elapsed,
        )
