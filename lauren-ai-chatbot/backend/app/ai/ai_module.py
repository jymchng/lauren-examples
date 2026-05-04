"""AIModule — wires LLMModule, banking agents, and delegation.

Architecture notes
------------------
``LLMModule.for_root()`` builds the transport + ``LLMService`` eagerly.

``AgentModule.for_root()`` wires the banking agents (BankingCRMAgent,
BankingTransferAgent) with their tools and the shared ``AgentRunner``.
Class-form tools that need DI dependencies (BankDatabase, specialist agents)
are auto-injected at startup.

One wiring singleton breaks a circular reference at construction time:
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

from lauren import module, use_value
from lauren_ai import (
    CostTracker,
    InMemoryConversationStore,
    LLMConfig,
    LLMModule,
    ModelCallComplete,
    default_pricing_table,
)
from lauren_ai._agents._runner import AgentRunner
from lauren_ai._module import AgentModule, LLMService
from lauren_ai._tools._registry import ToolRegistry

from app.ai.banking_delegation import BankingDelegationWiring, DelegateToBankingTransfer
from app.ai.banking_tools import GetBalanceTool, GetTransactionHistoryTool, TransferFundsTool
from app.ai.crm_agent import BankingCRMAgent
from app.ai.signals import signal_bus
from app.ai.transfer_agent import BankingTransferAgent
from app.banking.banking_module import BankingModule

logger = logging.getLogger(__name__)

# ── 1. LLM configuration (OpenRouter is OpenAI-compatible) ──────────────────

_llm_config = LLMConfig(
    provider="openai",
    model=os.environ.get("LLM_MODEL", "poolside/laguna-xs.2:free"),
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    base_url="https://openrouter.ai/api/v1",
)

LLMProvider = LLMModule.for_root(_llm_config)

# ── 2. Conversation store — persists message history across AgentRunner.run() calls ─
_conversation_store = InMemoryConversationStore()

# ── 3. Agent + tool wiring via AgentModule ───────────────────────────────────
#
# Banking agents share one AgentRunner.  Class-form tools are resolved by the
# DI container so their injectable deps (BankDatabase, specialist agents) are
# injected automatically.  BankingModule is imported so BankDatabase is visible.

_AgentProvider = AgentModule.for_root(
    agents=[
        BankingCRMAgent,
        BankingTransferAgent,
    ],
    tools=[
        # Banking tools (class-form, injected with BankDatabase)
        GetBalanceTool,
        TransferFundsTool,
        GetTransactionHistoryTool,
        # Banking delegation tool
        DelegateToBankingTransfer,
    ],
    imports=[LLMProvider, BankingModule],
    signals=signal_bus,
    conversation_store=_conversation_store,
)

# ── 4. CostTracker — accumulates token costs from ModelCallComplete signals ──

_cost_tracker = CostTracker(pricing=default_pricing_table())


@signal_bus.on(ModelCallComplete)
async def _track_cost(event: ModelCallComplete) -> None:
    """Accumulate token usage into the global CostTracker."""
    logger.debug("_track_cost: model=%s", getattr(event, "model", "?"))
    await _cost_tracker._on_model_call_complete(event)


_cost_tracker_provider = use_value(provide=CostTracker, value=_cost_tracker)


@module(
    imports=[LLMProvider, _AgentProvider, BankingModule],
    providers=[
        _cost_tracker_provider,
        # Banking delegation wiring
        BankingDelegationWiring,
    ],
    exports=[
        LLMService,
        AgentRunner,
        ToolRegistry,
        # Banking agents
        BankingCRMAgent,
        BankingTransferAgent,
        # Services
        CostTracker,
    ],
)
class AIModule:
    """Provides banking AI services: agents, runner, and cost tracker."""
