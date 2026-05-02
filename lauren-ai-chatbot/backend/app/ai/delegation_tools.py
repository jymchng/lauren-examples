# NOTE: Do NOT add `from __future__ import annotations` to this file.
# The @tool() decorator uses inspect.signature() at decoration time to build
# the JSON schema, and PEP 563 lazy evaluation breaks that introspection.
"""Delegation tools that route the orchestrator to specialist agents.

``init_delegation()`` must be called once at startup (from ai_module.py)
to wire the module-level singleton references.  Until then the tools return
an error payload rather than raising, so startup import errors remain clear.
"""

import logging

from lauren_ai import tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons — set by init_delegation()
# ---------------------------------------------------------------------------

_agent_runner = None   # AgentRunner
_research_agent = None  # ResearchAgent instance
_code_agent = None      # CodeAssistantAgent instance


def init_delegation(runner, research, code) -> None:
    """Wire the AgentRunner and specialist agent instances.

    Called once from ai_module.py after all agents are instantiated.

    :param runner: The shared AgentRunner singleton.
    :param research: An instantiated ResearchAgent.
    :param code: An instantiated CodeAssistantAgent.
    """
    global _agent_runner, _research_agent, _code_agent
    _agent_runner = runner
    _research_agent = research
    _code_agent = code


# ---------------------------------------------------------------------------
# Delegation tools
# ---------------------------------------------------------------------------


@tool()
async def delegate_to_researcher(task: str) -> dict:
    """Delegate a research or web-fetching task to the ResearchAgent.

    Use this tool when the user asks to fetch a URL, look something up online,
    or perform any information-gathering task.

    Args:
        task: A clear description of the research task including any URLs
              or topics to investigate.
    """
    if _agent_runner is None or _research_agent is None:
        return {
            "error": "ResearchAgent is not yet initialised. Call init_delegation() first.",
            "content": "",
        }
    try:
        response = await _agent_runner.run(_research_agent, task)
        return {
            "content": response.content,
            "turns": response.turns,
            "stop_reason": response.stop_reason,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("delegate_to_researcher failed: %s", exc)
        return {"error": str(exc), "content": ""}


@tool()
async def delegate_to_code_assistant(task: str) -> dict:
    """Delegate a code execution or mathematical analysis task to the CodeAssistantAgent.

    Use this tool when the user asks to run Python code, perform complex
    calculations, analyse data programmatically, or debug a script.

    Args:
        task: A clear description of the coding task including any code
              snippets or formulas to evaluate.
    """
    if _agent_runner is None or _code_agent is None:
        return {
            "error": "CodeAssistantAgent is not yet initialised. Call init_delegation() first.",
            "content": "",
        }
    try:
        response = await _agent_runner.run(_code_agent, task)
        return {
            "content": response.content,
            "turns": response.turns,
            "stop_reason": response.stop_reason,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("delegate_to_code_assistant failed: %s", exc)
        return {"error": str(exc), "content": ""}
