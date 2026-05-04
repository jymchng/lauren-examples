"""AIModule — wires LLMModule, banking agents, and delegation.

Architecture notes
------------------
Two ``AgentModule.for_root()`` calls are used to break the circular
dependency between the CRM runner and the delegation tool:

1. ``_TransferAgentProvider`` builds ``TransferAgentRunner`` (a subclass of
   ``AgentRunner`` used as a distinct DI token) and wires only the transfer
   tools.  No delegation tool → no cycle.

2. ``_CRMAgentProvider`` builds ``AgentRunner`` and wires
   ``DelegateToBankingTransfer``.  Because ``DelegateToBankingTransfer``
   injects ``TransferAgentRunner`` (not ``AgentRunner``), there is no
   circular dependency:

     AgentRunner (CRM) → DelegateToBankingTransfer → TransferAgentRunner

   The two tokens are distinct, so the DI container resolves them
   independently.

Observability
-------------
Both runners are wired to the shared ``signal_bus`` so every model call
emits ``ModelCallComplete`` events.  ``CostTracker`` accumulates usage and is
exported so controllers can inject it.
"""

from __future__ import annotations

import logging
import os

from lauren import module, use_value
from lauren_ai import (
    AgentRunner,
    CostTracker,
    InMemoryConversationStore,
    LLMConfig,
    LLMModule,
    ModelCallComplete,
    default_pricing_table,
)
from lauren_ai._module import AgentModule, LLMService

from app.ai.banking_delegation import DelegateToBankingTransfer, TransferAgentRunner
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

# ── 3. Agent + tool wiring via two AgentModule calls ────────────────────────
#
# The Transfer Agent module uses ``runner_class=TransferAgentRunner`` so its
# runner is registered under a distinct DI token.  This lets
# ``DelegateToBankingTransfer`` inject ``TransferAgentRunner`` without
# creating a cycle with the CRM ``AgentRunner``.

_TransferAgentModule = AgentModule.for_root(
    agents=[BankingTransferAgent],
    tools=[
        TransferFundsTool,
    ],
    imports=[LLMProvider, BankingModule],
    signals=signal_bus,
    conversation_store=_conversation_store,
    runner_class=TransferAgentRunner,
)

# The CRM Agent module imports _TransferAgentModule so that
# DelegateToBankingTransfer can see and inject TransferAgentRunner.
_CRMAgentModule = AgentModule.for_root(
    agents=[BankingCRMAgent],
    tools=[DelegateToBankingTransfer, GetBalanceTool, GetTransactionHistoryTool],
    imports=[LLMProvider, _TransferAgentModule, BankingModule],
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
    imports=[LLMProvider, _CRMAgentModule, _TransferAgentModule, BankingModule],
    providers=[
        _cost_tracker_provider,
    ],
    exports=[
        LLMService,
        AgentRunner,
        BankingCRMAgent,
        CostTracker,
    ],
)
class AIModule:
    """Provides banking AI services: agents, runners, and cost tracker."""
