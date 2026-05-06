"""AIModule — wires LLMModule, all four banking agents, and delegation.

Agent architecture
------------------
Four agents are wired in two language pairs:

  English pair:
    BankingCRMAgentEN   (CRMAgentRunner)
    BankingTransferAgentEN (TransferAgentRunner)

  Mandarin pair:
    BankingCRMAgentZH   (CRMAgentRunner)
    BankingTransferAgentZH (TransferAgentRunner)

Both CRM agents share CRMAgentRunner; both Transfer agents share
TransferAgentRunner.  AgentRunner.run(agent, prompt, ...) is stateless
and receives the agent instance as a parameter, so one runner token
serves either language variant.

CRM agents can hand off to either Transfer agent.
Transfer agents can hand back to either CRM agent.

Observability
-------------
Both runners are wired to the shared ``signal_bus`` so every model call
emits ``ModelCallComplete`` events.  ``CostTracker`` accumulates usage.
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

from app.ai.active_agent_module import ActiveAgentModule
from app.ai.active_agent_store import ActiveAgentStore
from app.ai.approval_module import ApprovalModule
from app.ai.banking_delegation import (
    CRMAgentRunner,
    TransferAgentRunner,
)
from app.ai.crm_agent import BankingCRMAgentEN
from app.ai.crm_agent_zh import BankingCRMAgentZH
from app.ai.handoff_tool import HandoffTo
from app.ai.signals import signal_bus
from app.ai.transfer_agent import BankingTransferAgentEN
from app.ai.transfer_agent_zh import BankingTransferAgentZH
from app.ai.chat_banking_controller import BankingChatController
from app.banking.banking_module import BankingModule
from app.crypto.crypto_module import CryptoModule
from app.ws.ws_module import WsModule

logger = logging.getLogger(__name__)

# ── 1. LLM configuration ────────────────────────────────────────────────────

_llm_config = LLMConfig(
    provider="openai",
    model=os.environ.get("LLM_MODEL", "poolside/laguna-xs.2:free"),
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    base_url="https://openrouter.ai/api/v1",
)

LLMProvider = LLMModule.for_root(_llm_config)

# ── 2. Conversation store ────────────────────────────────────────────────────

_conversation_store = InMemoryConversationStore()

# ── 3. Agent + tool wiring ──────────────────────────────────────────────────
#
# Two AgentModule instances: one for both CRM agents, one for both Transfer
# agents.  Placing language variants in the same module ensures each tool
# class is owned by exactly one module (avoids ModuleExportViolation).

_TransferAgentModule = AgentModule.for_root(
    agents=[BankingTransferAgentEN, BankingTransferAgentZH],
    tools=[
        HandoffTo[BankingCRMAgentEN, BankingCRMAgentZH],      # Transfer → CRM (either language)
    ],
    imports=[LLMProvider, BankingModule, ApprovalModule, WsModule, ActiveAgentModule],
    signals=signal_bus,
    conversation_store=_conversation_store,
    runner=TransferAgentRunner,
)

_CRMAgentModule = AgentModule.for_root(
    agents=[BankingCRMAgentEN, BankingCRMAgentZH],
    tools=[
        HandoffTo[BankingTransferAgentEN, BankingTransferAgentZH],  # CRM → Transfer (either language)
    ],
    imports=[LLMProvider, BankingModule, WsModule, ActiveAgentModule],
    signals=signal_bus,
    conversation_store=_conversation_store,
    runner=CRMAgentRunner,
)

# ── 4. CostTracker ──────────────────────────────────────────────────────────

_cost_tracker = CostTracker(pricing=default_pricing_table())


@signal_bus.on(ModelCallComplete)
async def _track_cost(event: ModelCallComplete) -> None:
    """Accumulate token usage into the global CostTracker."""
    logger.debug("_track_cost: model=%s", getattr(event, "model", "?"))
    await _cost_tracker._on_model_call_complete(event)


_cost_tracker_provider = use_value(provide=CostTracker, value=_cost_tracker)


@module(
    imports=[
        LLMProvider,
        _CRMAgentModule,
        _TransferAgentModule,
        BankingModule,
        CryptoModule,
        WsModule,
        ActiveAgentModule,
    ],
    providers=[
        _cost_tracker_provider,
    ],
    exports=[
        LLMService,
        BankingCRMAgentEN,
        BankingCRMAgentZH,
        BankingTransferAgentEN,
        BankingTransferAgentZH,
        ActiveAgentStore,
        CostTracker,
    ],
    controllers=[
        BankingChatController,
    ],
)
class AIModule:
    """Provides banking AI services: four agents, two runners, and cost tracker."""
