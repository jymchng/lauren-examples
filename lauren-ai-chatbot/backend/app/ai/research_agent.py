# NOTE: Do NOT add `from __future__ import annotations` to this file.
# The @tool() decorator uses inspect.signature() at decoration time to build
# the JSON schema, and PEP 563 lazy evaluation breaks that introspection.
"""ResearchAgent — fetches URLs and gathers information for the orchestrator."""

from lauren_ai import LengthFilter, PromptInjectionFilter, agent, guardrail, use_tools
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
@guardrail(
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
