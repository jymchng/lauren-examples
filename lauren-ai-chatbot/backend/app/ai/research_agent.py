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
