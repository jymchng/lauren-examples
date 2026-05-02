"""ChatAgent — the agentic chat assistant with access to utility tools."""

from __future__ import annotations

from lauren_ai import LengthFilter, PromptInjectionFilter, agent, guardrail, use_tools

from app.ai.tools import calculate, get_current_time, word_count


@agent(model="openai/gpt-4o-mini", system="You are a helpful assistant with access to tools.")
@guardrail(
    input=[PromptInjectionFilter()],
    output=[LengthFilter(max_chars=8000)],
)
@use_tools(get_current_time, calculate, word_count)
class ChatAgent:
    """Helpful assistant that can look up the current time, evaluate maths, and count words.

    Protected by:
    - Input: ``PromptInjectionFilter`` — blocks jailbreak / prompt-override attempts.
    - Output: ``LengthFilter`` — caps responses at 8 000 characters to prevent runaway output.
    """
