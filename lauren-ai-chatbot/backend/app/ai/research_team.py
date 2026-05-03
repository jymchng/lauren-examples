"""ResearchTeam — multi-agent team for deep research tasks.

The coordinator routes between a researcher (fetches / searches) and a code
assistant (runs calculations or data analysis) up to ``max_rounds`` times,
then synthesises a final answer.
"""

from __future__ import annotations

import logging

from lauren_ai import team

from app.ai.code_agent import CodeAssistantAgent
from app.ai.research_agent import ResearchAgent

_COORDINATOR_PROMPT = """\
You are coordinating a research team to complete the following task.

Available workers:
{worker_descriptions}

Task: {task}

Work completed so far:
{prior_outputs}

Decide the next step:
  ROUTE: researcher       — fetch URLs or gather information
  ROUTE: code_assistant   — run code or perform calculations
  DONE: <final answer>    — all required information has been gathered

Respond with exactly one of the above formats.
"""


@team(
    name="research-team",
    mode="coordinator",
    model="poolside/laguna-xs.2:free",
    max_rounds=4,
    coordinator_prompt=_COORDINATOR_PROMPT,
)
class ResearchTeam:
    """Multi-agent team: researcher + code assistant, coordinated by an LLM."""

    def __init__(
        self,
        researcher: ResearchAgent,
        code_assistant: CodeAssistantAgent,
    ) -> None:
        self.researcher = researcher
        self.code_assistant = code_assistant
