"""AIModule — wires LLMModule and all three banking agents.

Agent architecture
------------------
Three English-only agents in distinct modules:

  UnauthenticatedCRMAgent  (UnauthCRMRunner)     — public, pre-login
  AuthenticatedCRMAgent    (AuthCRMRunner)        — logged-in customers
  BankTransferAgent        (TransferAgentRunner)  — fund transfers

CheckAuthenticationTool is shared across all three agents.  It is owned and
exported by CheckAuthModule; each AgentModule imports CheckAuthModule and uses
shared_tools=[CheckAuthenticationTool] to prevent duplicate DI registration.

Observability
-------------
All runners are wired to the shared ``signal_bus`` so every model call emits
``ModelCallComplete`` events.  ``CostTracker`` accumulates usage.
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
from app.ai.auth_crm_agent import AuthenticatedCRMAgent
from app.ai.banking_delegation import AuthCRMRunner, TransferAgentRunner, UnauthCRMRunner
from app.ai.check_auth_module import CheckAuthModule
from app.ai.check_auth_tool import CheckAuthenticationTool
from app.ai.handoff_tool import HandoffTo
from app.ai.signals import signal_bus
from app.ai.transfer_agent import BankTransferAgent
from app.ai.unauth_crm_agent import UnauthenticatedCRMAgent
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
# Three AgentModule instances — one per agent.  CheckAuthenticationTool is
# shared; it is owned by CheckAuthModule and imported via shared_tools= to
# prevent ModuleExportViolation.

_UnauthCRMModule = AgentModule.for_root(
    agents=[UnauthenticatedCRMAgent],
    imports=[LLMProvider, CheckAuthModule, WsModule, ActiveAgentModule],
    shared_tools=[CheckAuthenticationTool],
    signals=signal_bus,
    conversation_store=_conversation_store,
    runner=UnauthCRMRunner,
)

_AuthCRMModule = AgentModule.for_root(
    agents=[AuthenticatedCRMAgent],
    tools=[HandoffTo[BankTransferAgent, UnauthenticatedCRMAgent]],
    imports=[LLMProvider, CheckAuthModule, BankingModule, WsModule, ActiveAgentModule],
    shared_tools=[CheckAuthenticationTool],
    signals=signal_bus,
    conversation_store=_conversation_store,
    runner=AuthCRMRunner,
)

_TransferModule = AgentModule.for_root(
    agents=[BankTransferAgent],
    tools=[HandoffTo[UnauthenticatedCRMAgent, AuthenticatedCRMAgent]],
    imports=[LLMProvider, CheckAuthModule, BankingModule, ApprovalModule, WsModule, ActiveAgentModule],
    shared_tools=[CheckAuthenticationTool],
    signals=signal_bus,
    conversation_store=_conversation_store,
    runner=TransferAgentRunner,
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
        _UnauthCRMModule,
        _AuthCRMModule,
        _TransferModule,
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
        UnauthenticatedCRMAgent,
        AuthenticatedCRMAgent,
        BankTransferAgent,
        ActiveAgentStore,
        CostTracker,
    ],
    controllers=[
        BankingChatController,
    ],
)
class AIModule:
    """Provides banking AI services: three agents, three runners, and cost tracker."""
