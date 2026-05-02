"""ChatAgent — the agentic chat assistant with access to utility tools."""

from __future__ import annotations

from lauren_ai import LengthFilter, PIIRedactor, PromptInjectionFilter, agent, guardrail, remember, use_tools

from app.ai.tools import calculate, get_current_time, word_count

# Shared in-memory user memory store — persists facts across runs within a
# single process lifetime.  Swap for a persistent backend in production.
from lauren_ai import InMemoryUserMemoryStore

_user_memory = InMemoryUserMemoryStore()


@agent(model="poolside/laguna-xs.2:free", system="You are a helpful assistant with access to tools.")
@remember(store=None, extract=True, inject=True, top_k=3)
@guardrail(
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
