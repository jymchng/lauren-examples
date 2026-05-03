"""CodeAssistantAgent — executes Python and analyses results for the orchestrator."""

from __future__ import annotations

from lauren_ai import LengthFilter, PromptInjectionFilter, agent, guardrail, use_tools
from lauren_ai._skills import CodeExecutionTool

from app.ai.tools import calculate, word_count


@agent(
    model="poolside/laguna-xs.2:free",
    system=(
        "You are a code assistant. "
        "Execute Python snippets and analyse the results. "
        "Always show the code you ran and explain the output."
    ),
)
@guardrail(
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
