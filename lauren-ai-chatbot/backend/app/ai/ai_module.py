"""AIModule — wires LLMModule and AgentModule into the application.

Architecture notes
------------------
``LLMModule.for_root()`` generates a ``@module`` that provides and exports
``Transport``, ``LLMService``, ``EmbedService``, and ``LLMConfig`` as
singleton ``use_value`` providers.

``AgentModule.for_root()`` generates a ``@module`` with the ``ToolRegistry``
and all ``@agent()``-decorated classes.  Its auto-generated ``use_factory``
for ``AgentRunner`` injects ``[Transport, ToolRegistry, LLMConfig]``, but
those tokens are only visible within ``_AgentModule``'s own scope — they
are NOT visible because ``_AgentModule`` does not import ``_LLMModule``.

To work around this, we *skip* the automatic ``AgentRunner`` wiring and
instead provide a pre-built ``AgentRunner`` as a ``use_value`` directly in
this ``AIModule``, where both ``LLMProvider``'s exports (including the
``Transport`` and ``LLMConfig`` instances) are fully accessible.

``AIModule`` exports ``LLMService`` so that ``ChatService`` (declared in
``ChatModule``) can receive it through the module visibility chain.

Observability
-------------
The ``AgentRunner`` is wired to the shared ``signal_bus`` (from
``app.ai.signals``) so every model call emits ``ModelCallComplete`` events.
``CostTracker`` accumulates usage in response to those signals and is also
exported so controllers can inject it for per-request cost reporting.
"""

from __future__ import annotations

import os

from lauren import module, use_value
from lauren_ai import CostTracker, LLMConfig, LLMModule, ModelCallComplete, default_pricing_table
from lauren_ai._agents._runner import AgentRunner
from lauren_ai._module import LLMService
from lauren_ai._tools._registry import ToolRegistry

from app.ai.agent import ChatAgent
from app.ai.signals import signal_bus
from app.ai.tools import calculate, get_current_time, word_count

# ── 1. LLM configuration (OpenRouter is OpenAI-compatible)

_llm_config = LLMConfig(
    provider="openai",
    model=os.environ.get("LLM_MODEL", "openai/gpt-4o-mini"),
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    base_url="https://openrouter.ai/api/v1",
)

LLMProvider = LLMModule.for_root(_llm_config)

# ── 2. Build the ToolRegistry and AgentRunner manually so we can provide them
#    via use_value.  This sidesteps the module-visibility issue that arises
#    when AgentModule's use_factory tries to inject Transport across module
#    boundaries.

_registry = ToolRegistry()
for _tool_fn in [get_current_time, calculate, word_count]:
    _registry.register(_tool_fn)

# Extract the LLMService/transport from the pre-built LLMProvider class.
_transport = LLMProvider.transport_instance  # type: ignore[attr-defined]
_llm_service = LLMProvider.llm_service_instance  # type: ignore[attr-defined]

_agent_runner = AgentRunner(
    transport=_transport,
    registry=_registry,
    config=_llm_config,
    signals=signal_bus,      # ← fire ModelCallComplete / ToolCallComplete events
    cache_backend=None,
)

# ── 3. CostTracker — accumulates token costs from ModelCallComplete signals

_cost_tracker = CostTracker(pricing=default_pricing_table())


@signal_bus.on(ModelCallComplete)
async def _track_cost(event: ModelCallComplete) -> None:
    """Accumulate token usage into the global CostTracker."""
    await _cost_tracker._on_model_call_complete(event)


# ── 4. Build providers list

_registry_provider = use_value(provide=ToolRegistry, value=_registry)
_runner_provider = use_value(provide=AgentRunner, value=_agent_runner)
_agent_provider = use_value(provide=ChatAgent, value=ChatAgent())
_cost_tracker_provider = use_value(provide=CostTracker, value=_cost_tracker)


@module(
    imports=[LLMProvider],
    providers=[
        _registry_provider,
        _runner_provider,
        _agent_provider,
        _cost_tracker_provider,
    ],
    exports=[LLMService, AgentRunner, ChatAgent, CostTracker],
)
class AIModule:
    """Provides LLMService, AgentRunner, ChatAgent, ToolRegistry, and CostTracker."""
