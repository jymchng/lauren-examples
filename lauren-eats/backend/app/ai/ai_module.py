"""AIModule — wires :class:`LLMModule` and all six agents.

P0 fixes:
- ``LLMConfig`` is constructed once (issues 9.1, 9.2) and handed to
  :meth:`LLMModule.for_root` — the hand-rolled ``httpx`` call in
  :class:`app.services.chat_service.ChatService` is gone (issue 9.3).
- :meth:`AgentModule.for_root` registers the runner and all agents
  (issue 10.1); ``ChatService`` resolves ``AgentRunner[ConciergeAgent]``
  and calls :meth:`run_stream` (issue 10.3).
- Agents use ``model=None`` so the LLMConfig default flows through
  (issue 10.7), and they include the ``HandoffTo`` tool — no more
  ``<<HANDOFF:...>>`` regex (issue 12.1).
- The signal bus is shared so every model call surfaces on
  :data:`app.ai.signals.signal_bus` (issue 7.2).
"""

from __future__ import annotations

from lauren import module
from lauren_ai import LLMModule

from app.ai.llm_config import llm_config
from app.ai.signals import signal_bus
from app.agents.concierge import ConciergeAgent
from app.agents.dietary import DietaryAgent
from app.agents.food_recommender import FoodRecommenderAgent
from app.agents.ordering_agent import OrderingAgent
from app.agents.reservation_agent import ReservationAgent
from app.agents.support import SupportAgent
from app.agents.tools import (
    CheckDietaryInfoTool,
    CheckOrderStatusTool,
    CreateOrderTool,
    CreateReservationTool,
    GetMenuItemDetailsTool,
    HandoffTo,
    SearchMenuTool,
)
from app.db.database_module import DatabaseModule


# LLM provider module — registered once at import time.
LLMProvider = LLMModule.for_root(llm_config)


def _build_agent_module():
    from lauren_ai import AgentModule

    return AgentModule.for_root(
        agents=[
            ConciergeAgent,
            FoodRecommenderAgent,
            DietaryAgent,
            OrderingAgent,
            ReservationAgent,
            SupportAgent,
        ],
        tools=[
            SearchMenuTool,
            GetMenuItemDetailsTool,
            CheckDietaryInfoTool,
            CreateOrderTool,
            CheckOrderStatusTool,
            CreateReservationTool,
            HandoffTo,
        ],
        # DatabaseModule is passed in ``imports=`` so the auto-generated
        # agent module can see ``DatabaseService`` for class-form tool DI.
        imports=[DatabaseModule, LLMProvider],
        signals=signal_bus,
    )


# All six agents share a single AgentModule so they share a single
# AgentRunner singleton (matches the securebank pattern of one
# AgentModule per functional cluster).
RestaurantAIAgents = _build_agent_module()


# Per-agent ``AgentRunner[AgentX]`` aliases.  These are re-exported from
# the auto-generated :class:`RestaurantAIAgents` module so consumers
# (e.g. :class:`app.services.chat_service.ChatService`) can inject a
# specific agent's runner by type.
from lauren_ai import AgentRunner as _Runner


@module(
    imports=[DatabaseModule, LLMProvider, RestaurantAIAgents],
    exports=[
        ConciergeAgent,
        FoodRecommenderAgent,
        DietaryAgent,
        OrderingAgent,
        ReservationAgent,
        SupportAgent,
        _Runner[ConciergeAgent],
        _Runner[FoodRecommenderAgent],
        _Runner[DietaryAgent],
        _Runner[OrderingAgent],
        _Runner[ReservationAgent],
        _Runner[SupportAgent],
    ],
)
class AIModule:
    """Wires the LLM stack and all six agents into a single importable module.

    Imports :class:`DatabaseModule` so the class-form tools (which depend
    only on :class:`app.db.database.DatabaseService`) can be DI-resolved
    without coupling the AI module to menu / order / reservation feature
    modules.
    """
