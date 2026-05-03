"""Delegation tools that route the orchestrator to specialist agents.

Both tools are class-form ``@tool()`` classes so Lauren's DI container resolves
their specialist-agent dependencies at startup.

``AgentRunner`` is intentionally **not** a constructor dependency — that would
create a circular dependency (AgentRunner → ToolRegistry → tool → AgentRunner).
Instead, ``DelegationWiring`` is a DI singleton whose constructor receives the
fully-built ``AgentRunner`` and the two tool instances, then wires them together.
Lauren's lifecycle scheduler eagerly instantiates every singleton at startup, so
the wiring always completes before the first request arrives.
"""

from __future__ import annotations

import logging

from lauren import Scope, injectable
from lauren_ai import tool
from lauren_ai._agents._runner import AgentRunner

from app.ai.code_agent import CodeAssistantAgent
from app.ai.research_agent import ResearchAgent

logger = logging.getLogger(__name__)


@tool()
class DelegateToResearcher:
    """Delegate a research or web-fetching task to the ResearchAgent.

    Use this tool when the user asks to fetch a URL, look something up online,
    or perform any information-gathering task.

    Args:
        task: A clear description of the research task including any URLs
              or topics to investigate.
    """

    def __init__(self, research: ResearchAgent) -> None:
        self._research = research
        # Set by DelegationWiring after the full DI graph is built.
        self._runner: AgentRunner | None = None

    async def run(self, task: str) -> dict:
        """Run the delegation to the ResearchAgent."""
        if self._runner is None:
            return {
                "error": "AgentRunner not yet wired. Ensure DelegationWiring is in AIModule providers.",
                "content": "",
            }
        try:
            response = await self._runner.run(self._research, task)
            return {
                "content": response.content,
                "turns": response.turns,
                "stop_reason": response.stop_reason,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("DelegateToResearcher failed: %s", exc)
            return {"error": str(exc), "content": ""}


@tool()
class DelegateToCodeAssistant:
    """Delegate a code execution or mathematical analysis task to the CodeAssistantAgent.

    Use this tool when the user asks to run Python code, perform complex
    calculations, analyse data programmatically, or debug a script.

    Args:
        task: A clear description of the coding task including any code
              snippets or formulas to evaluate.
    """

    def __init__(self, code: CodeAssistantAgent) -> None:
        self._code = code
        # Set by DelegationWiring after the full DI graph is built.
        self._runner: AgentRunner | None = None

    async def run(self, task: str) -> dict:
        """Run the delegation to the CodeAssistantAgent."""
        if self._runner is None:
            return {
                "error": "AgentRunner not yet wired. Ensure DelegationWiring is in AIModule providers.",
                "content": "",
            }
        try:
            response = await self._runner.run(self._code, task)
            return {
                "content": response.content,
                "turns": response.turns,
                "stop_reason": response.stop_reason,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("DelegateToCodeAssistant failed: %s", exc)
            return {"error": str(exc), "content": ""}


@injectable(scope=Scope.SINGLETON)
class DelegationWiring:
    """Wires ``AgentRunner`` into delegation tools after the DI graph is built.

    Dependency order at startup:
    1. ``ResearchAgent``, ``CodeAssistantAgent``  (no deps)
    2. ``DelegateToResearcher(research)``, ``DelegateToCodeAssistant(code)``
    3. ``ToolRegistry`` built with the tool instances above
    4. ``AgentRunner`` built with Transport + ToolRegistry + LLMConfig
    5. **``DelegationWiring``** — receives AgentRunner + the two tool instances
       and sets their ``_runner`` attribute

    Lauren's lifecycle scheduler eagerly resolves every singleton at startup
    (``LifecycleScheduler.run_post_construct``), so this wiring always completes
    before the first request arrives.
    """

    def __init__(
        self,
        runner: AgentRunner,
        delegate_researcher: DelegateToResearcher,
        delegate_code: DelegateToCodeAssistant,
    ) -> None:
        delegate_researcher._runner = runner
        delegate_code._runner = runner
        logger.debug("DelegationWiring: AgentRunner wired into delegation tools")
