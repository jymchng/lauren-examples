"""AIModule — wires LLMModule, agents, teams, and delegation.

Architecture notes
------------------
``LLMModule.for_root()`` builds the transport + ``LLMService`` eagerly.

``AgentModule.for_root()`` wires ALL agents (general-purpose + banking) with
their tools and the shared ``AgentRunner``.  Class-form tools that need DI
dependencies (BankDatabase, specialist agents) are auto-injected at startup.

Two wiring singletons break circular references at construction time:
  - ``DelegationWiring``        → sets AgentRunner on DelegateToResearcher/CodeAssistant
  - ``BankingDelegationWiring`` → sets AgentRunner on DelegateToBankingTransfer

Observability
-------------
The ``AgentRunner`` is wired to the shared ``signal_bus`` so every model call
emits ``ModelCallComplete`` events.  ``CostTracker`` accumulates usage and is
exported so controllers can inject it.
"""

from __future__ import annotations

import logging
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
from app.ai.banking_delegation import BankingDelegationWiring, DelegateToBankingTransfer
from app.ai.banking_tools import GetBalanceTool, GetTransactionHistoryTool, TransferFundsTool
from app.ai.code_agent import CodeAssistantAgent
from app.ai.crm_agent import BankingCRMAgent
from app.ai.delegation_tools import (
    DelegateToCodeAssistant,
    DelegateToResearcher,
    DelegationWiring,
)
from app.ai.orchestrator_agent import OrchestratorAgent
from app.ai.research_agent import ResearchAgent
from app.ai.research_team import ResearchTeam
from app.ai.signals import signal_bus
from app.ai.transfer_agent import BankingTransferAgent
from app.banking.banking_module import BankingModule

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
# All agents (general-purpose and banking) share one AgentRunner.
# Class-form tools are resolved by the DI container so their injectable deps
# (BankDatabase, specialist agents) are injected automatically.
# BankingModule is imported so BankDatabase is visible to banking tools.

_AgentProvider = AgentModule.for_root(
    agents=[
        # General-purpose agents
        ChatAgent,
        OrchestratorAgent,
        ResearchAgent,
        CodeAssistantAgent,
        # Banking agents
        BankingCRMAgent,
        BankingTransferAgent,
    ],
    tools=[
        # General-purpose delegation tools
        DelegateToResearcher,
        DelegateToCodeAssistant,
        # Banking tools (class-form, injected with BankDatabase)
        GetBalanceTool,
        TransferFundsTool,
        GetTransactionHistoryTool,
        # Banking delegation tool
        DelegateToBankingTransfer,
    ],
    imports=[LLMProvider, BankingModule],
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
    imports=[LLMProvider, _AgentProvider, BankingModule],
    providers=[
        _cost_tracker_provider,
        _team_runner_provider,
        # General delegation wiring
        DelegationWiring,
        # Banking delegation wiring
        BankingDelegationWiring,
    ],
    exports=[
        LLMService,
        AgentRunner,
        ToolRegistry,
        # General-purpose agents
        ChatAgent,
        ResearchAgent,
        CodeAssistantAgent,
        OrchestratorAgent,
        # Banking agents
        BankingCRMAgent,
        BankingTransferAgent,
        # Services
        TeamRunner,
        CostTracker,
    ],
)
class AIModule:
    """Provides all AI services: agents, runner, team runner, and cost tracker."""
