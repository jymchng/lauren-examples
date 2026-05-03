"""ChatAgent — the agentic chat assistant with access to utility tools."""

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
    remember,
    use_guardrails,
    use_tools,
)

from app.ai.tools import calculate, get_current_time, word_count

# Shared in-memory user memory store — persists facts across runs within a
# single process lifetime.  Swap for a persistent backend in production.
from lauren_ai import InMemoryUserMemoryStore

_user_memory = InMemoryUserMemoryStore()

logger = logging.getLogger(__name__)


@agent(model="poolside/laguna-xs.2:free", system="You are a helpful assistant with access to tools.")
@remember(store=None, extract=True, inject=True, top_k=3)
@use_guardrails(
    input=[PromptInjectionFilter(), PIIRedactor()],
    output=[LengthFilter(max_chars=8000)],
)
@use_tools(get_current_time, calculate, word_count)
class ChatAgent:
    """Helpful assistant that can look up the current time, evaluate maths, and count words.

    Protected by:
    - Input: ``PromptInjectionFilter`` — blocks jailbreak / prompt-override attempts.
    - Input: ``PIIRedactor`` — redacts sensitive personal information before model sees it.
    - Output: ``LengthFilter`` — caps responses at 8 000 characters to prevent runaway output.
    - Memory: ``@remember`` — injects up to 3 relevant past facts; extracts new facts after each turn.
    """

    async def on_start(self, ctx: AgentContext) -> None:
        ctx.metadata["_start"] = time.monotonic()
        logger.debug("ChatAgent.on_start: turn=%d", ctx.turn)

    async def on_turn_complete(self, completion: Completion, ctx: AgentContext) -> None:
        logger.debug(
            "ChatAgent.on_turn_complete: turn=%d content_len=%d",
            ctx.turn,
            len(completion.content or ""),
        )

    async def on_tool_result(self, result: ToolResult, ctx: AgentContext) -> ToolResult | None:
        if result.is_error:
            logger.debug("ChatAgent.on_tool_result: id=%s ERROR: %s", result.tool_use_id, result.content)
        else:
            logger.debug("ChatAgent.on_tool_result: id=%s ok len=%d", result.tool_use_id, len(str(result.content)))
        return None

    async def on_finish(self, response: AgentResponse, ctx: AgentContext) -> None:
        elapsed = time.monotonic() - ctx.metadata.get("_start", time.monotonic())
        logger.debug(
            "ChatAgent.on_finish: turns=%d stop=%s elapsed=%.3fs",
            response.turns,
            response.stop_reason,
            elapsed,
        )
