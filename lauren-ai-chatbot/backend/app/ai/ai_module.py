"""AIModule — wires LLMModule, agents, teams, and delegation.

Architecture notes
------------------
``LLMModule.for_root()`` builds the transport + ``LLMService`` eagerly and
exposes them as ``use_value`` providers (plus class attributes
``transport_instance`` / ``llm_service_instance`` for immediate access).

The chatbot uses **manual** agent and runner wiring (rather than
``AgentModule.for_root()``) for three reasons that all require access to the
fully-built ``AgentRunner`` instance *at module-definition time*:

1. **Delegation wiring** — ``init_delegation()`` must be called synchronously
   after the specialist agents are instantiated so the delegation tool
   closures capture live agent references before any request arrives.
2. **Signal bus** — the runner must be constructed with ``signals=signal_bus``
   so ``ModelCallComplete`` events drive the ``CostTracker``.
3. **TeamRunner** — needs the same ``AgentRunner`` instance the agents use.

For applications that do not need delegation or a custom signal bus,
``AgentModule.for_root(imports=LLMProvider)`` is the right pattern — passing
the LLM module via ``imports`` makes ``Transport`` and ``LLMConfig`` visible
inside the generated agent module so its ``use_factory`` resolves correctly::

    LLMProvider = LLMModule.for_root(llm_config)
    AIAgentModule = AgentModule.for_root(
        agents=[MyAgent],
        tools=[my_tool],
        imports=LLMProvider,   # ← fixes module-visibility for Transport
        signals=my_bus,
    )

Observability
-------------
The ``AgentRunner`` is wired to the shared ``signal_bus`` so every model call
emits ``ModelCallComplete`` events.  ``CostTracker`` accumulates usage in
response to those signals and is exported so controllers can inject it.
``TokenBudget`` caps per-conversation cost at $0.50 to prevent runaway charges.
"""

from __future__ import annotations

import os

from lauren import module, use_value
from lauren_ai import (
    CostTracker,
    LLMConfig,
    LLMModule,
    ModelCallComplete,
    TeamRunner,
    TokenBudget,
    default_pricing_table,
)
from lauren_ai._agents._runner import AgentRunner
from lauren_ai._module import LLMService
from lauren_ai._tools._registry import ToolRegistry

from app.ai.agent import ChatAgent
from app.ai.code_agent import CodeAssistantAgent
from app.ai.delegation_tools import delegate_to_code_assistant, delegate_to_researcher, init_delegation
from app.ai.orchestrator_agent import OrchestratorAgent
from app.ai.research_agent import ResearchAgent
from app.ai.research_team import ResearchTeam
from app.ai.signals import signal_bus
from app.ai.tools import calculate, get_current_time, word_count

# ── 1. LLM configuration (OpenRouter is OpenAI-compatible)

_llm_config = LLMConfig(
    provider="openai",
    model=os.environ.get("LLM_MODEL", "poolside/laguna-xs.2:free"),
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    base_url="https://openrouter.ai/api/v1",
)

LLMProvider = LLMModule.for_root(_llm_config)

# ── 2. Build the ToolRegistry and AgentRunner manually.
#    This is a deliberate choice: we need the AgentRunner instance available
#    immediately so we can pass it to init_delegation() and TeamRunner, and
#    wire it to the signal bus — all before the DI container starts.

_registry = ToolRegistry()
for _tool_fn in [get_current_time, calculate, word_count, delegate_to_researcher, delegate_to_code_assistant]:
    _registry.register(_tool_fn)

# Also register built-in skill tools used by specialist agents
from lauren_ai._skills import CodeExecutionTool, HttpFetchTool  # noqa: E402

for _skill_fn in [HttpFetchTool, CodeExecutionTool]:
    _registry.register(_skill_fn)

# Extract the LLMService/transport from the pre-built LLMProvider class.
_transport = LLMProvider.transport_instance  # type: ignore[attr-defined]
_llm_service = LLMProvider.llm_service_instance  # type: ignore[attr-defined]

# Token budget: cap per-conversation at $0.50 to prevent runaway costs.
# Applied as a guard middleware when using token_budget_guard().
_token_budget = TokenBudget(max_usd_per_conversation=0.50)

_agent_runner = AgentRunner(
    transport=_transport,
    registry=_registry,
    config=_llm_config,
    signals=signal_bus,      # ← fire ModelCallComplete / ToolCallComplete events
    cache_backend=None,
)

# ── 3. Specialist agents

_research_agent = ResearchAgent()
_code_agent = CodeAssistantAgent()

# Wire delegation tools so OrchestratorAgent can route to specialists.
init_delegation(_agent_runner, _research_agent, _code_agent)

# ── 4. Top-level agents

_chat_agent = ChatAgent()
_orchestrator_agent = OrchestratorAgent()

# ── 5. TeamRunner for ResearchTeam

_team_runner = TeamRunner(
    team_cls=ResearchTeam,
    llm=_llm_service,
    agent_runner=_agent_runner,
)

# ── 6. CostTracker — accumulates token costs from ModelCallComplete signals

_cost_tracker = CostTracker(pricing=default_pricing_table())


@signal_bus.on(ModelCallComplete)
async def _track_cost(event: ModelCallComplete) -> None:
    """Accumulate token usage into the global CostTracker."""
    await _cost_tracker._on_model_call_complete(event)


# ── 7. Build providers list

_registry_provider = use_value(provide=ToolRegistry, value=_registry)
_runner_provider = use_value(provide=AgentRunner, value=_agent_runner)
_agent_provider = use_value(provide=ChatAgent, value=_chat_agent)
_research_agent_provider = use_value(provide=ResearchAgent, value=_research_agent)
_code_agent_provider = use_value(provide=CodeAssistantAgent, value=_code_agent)
_orchestrator_provider = use_value(provide=OrchestratorAgent, value=_orchestrator_agent)
_team_runner_provider = use_value(provide=TeamRunner, value=_team_runner)
_cost_tracker_provider = use_value(provide=CostTracker, value=_cost_tracker)


@module(
    imports=[LLMProvider],
    providers=[
        _registry_provider,
        _runner_provider,
        _agent_provider,
        _research_agent_provider,
        _code_agent_provider,
        _orchestrator_provider,
        _team_runner_provider,
        _cost_tracker_provider,
    ],
    exports=[
        LLMService,
        AgentRunner,
        ChatAgent,
        ResearchAgent,
        CodeAssistantAgent,
        OrchestratorAgent,
        TeamRunner,
        CostTracker,
    ],
)
class AIModule:
    """Provides all AI services: agents, runner, team runner, and cost tracker."""
