"""AIModule — wires LLMModule, agents, teams, and delegation.

Architecture notes
------------------
``LLMModule.for_root()`` builds the transport + ``LLMService`` eagerly and
exposes them as ``use_value`` providers (plus class attributes
``transport_instance`` / ``llm_service_instance`` for immediate access).

``AgentModule.for_root()`` wires the ``ToolRegistry`` and ``AgentRunner``
via ``use_factory`` providers so the DI container resolves them at startup.
Class-form tools (``DelegateToResearcher``, ``DelegateToCodeAssistant``) are
auto-injected with their specialist-agent dependencies.  ``DelegationWiring``
(a singleton in ``AIModule.providers``) then sets their ``_runner`` attribute
to the fully-built ``AgentRunner`` — breaking the would-be DI cycle without
``init_delegation()`` calls or module-level globals.

Observability
-------------
The ``AgentRunner`` is wired to the shared ``signal_bus`` so every model call
emits ``ModelCallComplete`` events.  ``CostTracker`` accumulates usage in
response to those signals and is exported so controllers can inject it.
``TokenBudget`` caps per-conversation cost at $0.50 to prevent runaway charges.
"""

from __future__ import annotations

import os

from lauren import module, use_factory, use_value
from lauren_ai import (
    CostTracker,
    LLMConfig,
    LLMModule,
    ModelCallComplete,
    TeamRunner,
    default_pricing_table,
)
from lauren_ai._agents._runner import AgentRunner
from lauren_ai._module import AgentModule, LLMService
from lauren_ai._tools._registry import ToolRegistry

from app.ai.agent import ChatAgent
from app.ai.code_agent import CodeAssistantAgent
from app.ai.delegation_tools import (
    DelegateToCodeAssistant,
    DelegateToResearcher,
    DelegationWiring,
)
from app.ai.orchestrator_agent import OrchestratorAgent
from app.ai.research_agent import ResearchAgent
from app.ai.research_team import ResearchTeam
from app.ai.signals import signal_bus

# ── 1. LLM configuration (OpenRouter is OpenAI-compatible) ──────────────────

_llm_config = LLMConfig(
    provider="openai",
    model=os.environ.get("LLM_MODEL", "poolside/laguna-xs.2:free"),
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    base_url="https://openrouter.ai/api/v1",
)

LLMProvider = LLMModule.for_root(_llm_config)

# ── 2. Agent + tool wiring via AgentModule ───────────────────────────────────
#
# AgentModule.for_root() registers:
# - All @agent()-decorated classes as @injectable(scope=SINGLETON) providers
# - Function-form tools immediately in the ToolRegistry
# - Class-form tools (DelegateToResearcher, DelegateToCodeAssistant) as DI
#   providers; the ToolRegistry is built lazily so the container injects the
#   fully-resolved tool instances (with their specialist-agent dependencies)
# - AgentRunner via use_factory, injecting Transport + ToolRegistry + LLMConfig
#
# Passing imports=LLMProvider makes Transport and LLMConfig visible inside the
# generated module so the AgentRunner factory can resolve them.
#
# DelegationWiring is registered as a provider in AIModule so that Lauren's
# lifecycle scheduler instantiates it at startup, wiring the fully-built
# AgentRunner into the delegation tools' _runner attribute.

_AgentProvider = AgentModule.for_root(
    agents=[ChatAgent, OrchestratorAgent, ResearchAgent, CodeAssistantAgent],
    tools=[DelegateToResearcher, DelegateToCodeAssistant],
    imports=LLMProvider,
    signals=signal_bus,
)

# ── 3. CostTracker — accumulates token costs from ModelCallComplete signals ──

_cost_tracker = CostTracker(pricing=default_pricing_table())


@signal_bus.on(ModelCallComplete)
async def _track_cost(event: ModelCallComplete) -> None:
    """Accumulate token usage into the global CostTracker."""
    await _cost_tracker._on_model_call_complete(event)


_cost_tracker_provider = use_value(provide=CostTracker, value=_cost_tracker)

# ── 4. TeamRunner for ResearchTeam (needs AgentRunner from DI) ──────────────

_team_runner_provider = use_factory(
    provide=TeamRunner,
    factory=lambda llm, runner: TeamRunner(
        team_cls=ResearchTeam,
        llm=llm,
        agent_runner=runner,
    ),
    inject=[LLMService, AgentRunner],
)


@module(
    imports=[LLMProvider, _AgentProvider],
    providers=[
        _cost_tracker_provider,
        _team_runner_provider,
        DelegationWiring,
    ],
    exports=[
        LLMService,
        AgentRunner,
        ToolRegistry,
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
