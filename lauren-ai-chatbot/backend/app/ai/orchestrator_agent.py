# NOTE: Do NOT add `from __future__ import annotations` to this file.
# The @tool() decorator uses inspect.signature() at decoration time to build
# the JSON schema, and PEP 563 lazy evaluation breaks that introspection.
"""OrchestratorAgent — top-level agent that routes to specialist sub-agents.

Architecture
------------
The orchestrator receives every user message from the /api/agent/ endpoint.
It decides which specialist to delegate to (or answers directly) based on the
nature of the request:

- Research / URL fetching   → ``delegate_to_researcher``
- Code execution / maths    → ``delegate_to_code_assistant``
- General questions          → answers directly with its own knowledge
"""

from lauren_ai import LengthFilter, PIIRedactor, PromptInjectionFilter, agent, guardrail, use_tools

from app.ai.delegation_tools import delegate_to_code_assistant, delegate_to_researcher
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


@agent(model="poolside/laguna-xs.2:free", system=_SYSTEM)
@guardrail(
    input=[PromptInjectionFilter(), PIIRedactor()],
    output=[LengthFilter(max_chars=8000)],
)
@use_tools(delegate_to_researcher, delegate_to_code_assistant, get_current_time)
class OrchestratorAgent:
    """Top-level routing agent with access to specialist sub-agents.

    Protected by:
    - Input: ``PromptInjectionFilter`` + ``PIIRedactor`` — blocks jailbreaks and
      redacts sensitive personal information before it reaches the model.
    - Output: ``LengthFilter`` — caps responses at 8 000 characters.
    """
