"""AIModule — wires LLMModule and all four banking agents.

Agent architecture
------------------
Four English-only agents distributed across three modules:

  UnauthenticatedCRMAgent  — public, pre-login
  AuthenticatedCRMAgent + DisputesAgent  — share an AgentModule for tool reuse
  BankTransferAgent  — fund transfers

Per-agent state
---------------
Each agent declares its **own** :class:`InMemoryConversationStore` via
``@agent(conversation_store=…)``.  Sharing a single store means every agent
sees the complete cross-agent turn history, which causes confusion — agents
may re-read prior handoff summaries as instructions and trigger the wrong
``HandoffTo`` call.  Per-agent stores keep contexts isolated; the handoff
summary passed via ``HandoffTo`` provides just the right amount of context.

CheckAuthenticationTool is shared across all four agents.  It is owned and
exported by CheckAuthModule; each AgentModule imports CheckAuthModule and uses
shared_tools=[CheckAuthenticationTool] to prevent duplicate DI registration.

Cross-module DI
---------------
``BankingChatController`` injects each runner via ``AgentRunner[AgentX]``
(see :class:`lauren_ai._agents._runner.AgentRunner.__class_getitem__`) — no
named runner subclasses needed; the framework synthesizes a fresh runner
class per ``AgentModule.for_root`` call and aliases ``AgentRunner[AgentX]``
to it for every agent in ``agents=``.

Observability
-------------
All runners are wired to the shared ``signal_bus`` so every model call emits
``ModelCallComplete`` events.  ``CostTracker`` accumulates usage.
"""

from __future__ import annotations

import logging

from lauren import module, use_value
from lauren_ai import (
    CostTracker,
    LLMModule,
    ModelCallComplete,
    default_pricing_table,
)
from app.ai.llm_config import llm_config as _llm_config
from lauren_ai._module import AgentModule, LLMService

from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent
from app.ai.agents.disputes_agent import DisputesAgent
from app.ai.agents.transfer_agent import BankTransferAgent
from app.ai.agents.unauth_crm_agent import UnauthenticatedCRMAgent
from app.ai.approval.approval_module import ApprovalModule
from app.ai.chat_banking_controller import BankingChatController
from app.ai.knowledge_sources import PUBLIC_KB_SOURCE
from app.ai.signals import signal_bus
from app.ai.tools.active_agent_module import ActiveAgentModule
from app.ai.tools.active_agent_store import ActiveAgentStore
from app.ai.tools.banking_tools import GetBalanceTool, GetTransactionHistoryTool
from app.ai.tools.check_auth_module import CheckAuthModule
from app.ai.tools.check_auth_tool import CheckAuthenticationTool
from app.ai.tools.handoff_tool import HandoffTo
from app.banking.banking_module import BankingModule
from app.crypto.crypto_module import CryptoModule
from app.ws.ws_module import WsModule

logger = logging.getLogger(__name__)

# ── 1. LLM configuration ────────────────────────────────────────────────────
# _llm_config is imported from app.ai.llm_config (above) to avoid circular
# imports: agent files import LLMScopeGuard which needs the config, and they
# cannot import from ai_module.py because ai_module.py imports the agents.

LLMProvider = LLMModule.for_root(_llm_config)

# ── 2. Agent + tool wiring ──────────────────────────────────────────────────
#
# AgentModule instances.  CheckAuthenticationTool is shared; it is owned by
# CheckAuthModule and imported via shared_tools= to prevent
# ModuleExportViolation.  Conversation stores are declared per-agent on the
# @agent(conversation_store=…) decorator — not at module level.

_UnauthCRMModule = AgentModule.for_root(
    agents=[UnauthenticatedCRMAgent],
    imports=[LLMProvider, CheckAuthModule, WsModule, ActiveAgentModule],
    shared_tools=[CheckAuthenticationTool],
    signals=signal_bus,
    # RAG: products, rates, fees, branch hours, account-opening, security.
    # Visibility is opt-in; UnauthenticatedCRMAgent declares it via
    # @use_knowledge_sources(PUBLIC_KB_SOURCE).
    knowledge=[PUBLIC_KB_SOURCE],
)

_AuthCRMModule = AgentModule.for_root(
    agents=[AuthenticatedCRMAgent],
    tools=[HandoffTo[BankTransferAgent, DisputesAgent]],
    imports=[LLMProvider, CheckAuthModule, BankingModule, WsModule, ActiveAgentModule],
    shared_tools=[CheckAuthenticationTool, GetBalanceTool, GetTransactionHistoryTool],
    signals=signal_bus,
)

_TransferModule = AgentModule.for_root(
    agents=[BankTransferAgent],
    tools=[HandoffTo[AuthenticatedCRMAgent, DisputesAgent]],
    imports=[LLMProvider, CheckAuthModule, BankingModule, ApprovalModule, WsModule, ActiveAgentModule],
    shared_tools=[CheckAuthenticationTool],
    signals=signal_bus,
)

_DisputesModule = AgentModule.for_root(
    agents=[DisputesAgent],
    tools=[HandoffTo[BankTransferAgent, AuthenticatedCRMAgent]],
    imports=[LLMProvider, CheckAuthModule, BankingModule, WsModule, ActiveAgentModule],
    shared_tools=[CheckAuthenticationTool, GetBalanceTool, GetTransactionHistoryTool],
    signals=signal_bus,
)


# ── 3. CostTracker ──────────────────────────────────────────────────────────

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
        _DisputesModule,
        BankingModule,
        CryptoModule,
        WsModule,
        ActiveAgentModule,
        ApprovalModule,
    ],
    providers=[
        _cost_tracker_provider,
    ],
    exports=[
        LLMService,
        UnauthenticatedCRMAgent,
        AuthenticatedCRMAgent,
        BankTransferAgent,
        DisputesAgent,
        ActiveAgentStore,
        CostTracker,
    ],
    controllers=[
        BankingChatController,
    ],
)
class AIModule:
    """Provides banking AI services: four agents, four runners, and cost tracker."""
