
# The @tool() decorator uses inspect.signature() at decoration time to build
# the JSON schema, and PEP 563 lazy evaluation breaks that introspection.
"""Conversation handoff tool for agent-to-agent session transfer.

``HandoffTo[AgentA]`` exposes a tool whose JSON schema lists AgentA's display
name as the only valid ``to_agent`` value.  ``HandoffTo[AgentA, AgentB]``
exposes both names in an ``enum`` so the LLM can choose between them at
call time.  Each distinct subscript produces a separate tool class with its
own DI token — the framework registers and injects them independently.

Flow (CRM → Transfer):
  1. CRM calls ``HandoffTo(to_agent="Banking Transfer Agent", summary="...")``
  2. Tool sets ``active_agent = TRANSFER_AGENT_NAME`` in ``ActiveAgentStore``
  3. Tool emits ``agent_handoff`` WebSocket event so the frontend can update
     the active-agent indicator
  4. Controller detects the change and routes the next turn to TransferAgent

Return flow (Transfer → CRM):
  1. Transfer calls ``HandoffTo(to_agent="Banking CRM Agent", summary="...")``
  2. Tool sets ``active_agent = CRM_AGENT_NAME`` in ``ActiveAgentStore``
  3. Tool emits a reverse ``agent_handoff`` WebSocket event
  4. Controller routes back to CRM for the confirmation message

Security:
  ``execution_context`` is forwarded intact through both agent runners, so the
  authenticated ``user_id`` (pinned by ``SignatureGuard``) never changes across
  the handoff boundary.
"""

import logging
from typing import ClassVar, Literal

from lauren_ai import ToolContext, tool

from app.ai.tools.active_agent_store import ActiveAgentStore
from app.ws.event_forwarder import EventForwarder

logger = logging.getLogger(__name__)


def _agent_display_name(agent_cls: type) -> str:
    """Return the display name from an @agent()-decorated class."""
    from lauren_ai._agents import AGENT_META  # lazy import — avoids cycle

    meta = getattr(agent_cls, AGENT_META, None)
    return meta.name if (meta and meta.name) else agent_cls.__name__


@tool()
class HandoffTo:
    """Hand the active conversation off to one of the available specialist agents.

    Call this when the customer's request is better handled by another agent.
    Choose the most appropriate agent from the ``to_agent`` options and provide
    a brief summary of what has been discussed so the receiving agent has context.

    Args:
        to_agent:  The agent to hand off to (must be one of the listed options).
        summary:   Brief summary of the conversation so far and why handing off.
    """

    _target_names: ClassVar[tuple[str, ...]] = ()
    _cache: ClassVar[dict[tuple[type, ...], type]] = {}

    def __init__(
        self,
        active_agent_store: ActiveAgentStore,
        event_forwarder: EventForwarder,
    ) -> None:
        self._store = active_agent_store
        self._forwarder = event_forwarder

    @classmethod
    def __class_getitem__(cls, agents: type | tuple[type, ...]) -> type:
        if not isinstance(agents, tuple):
            agents = (agents,)

        if agents in cls._cache:
            return cls._cache[agents]

        names: tuple[str, ...] = tuple(_agent_display_name(a) for a in agents)

        # Construct Literal[name1, name2, ...] dynamically.
        # Python compiles `Literal["a", "b"]` as `Literal.__getitem__(("a", "b"))`,
        # so passing the names tuple directly replicates that behaviour for all N.
        AgentChoice = Literal.__getitem__(names)

        async def run(self, ctx: ToolContext, to_agent: AgentChoice, summary: str) -> dict:
            return await self._run_handoff(ctx, to_agent, summary)

        new_cls = type(
            cls.__name__,
            (cls,),
            {
                "__doc__": cls.__doc__,
                "run": run,
                "_target_names": names,
            },
        )

        from lauren_ai import tool as _tool  # avoid shadowing outer name

        new_cls = _tool()(new_cls)

        cls._cache[agents] = new_cls
        return new_cls

    async def _run_handoff(self, ctx: ToolContext, to_agent: str, summary: str) -> dict:
        """Shared implementation called by every specialised run()."""
        if to_agent not in self._target_names:
            return {"error": f"Unknown agent {to_agent!r}. Valid choices: {list(self._target_names)}"}

        conversation_id: str = ctx.agent_context.metadata.get("conversation_id", "")
        from_name: str = ctx.agent_context.agent_name
        user_id: str = (
            ctx.execution_context.request.state.get("user_id")
            if ctx.execution_context and ctx.execution_context.request and ctx.execution_context.request.state
            else None
        ) or ""

        if conversation_id:
            self._store.set(conversation_id, to_agent)
            self._store.set_pending_summary(conversation_id, summary)

        await self._forwarder.send_to_user(
            user_id,
            {
                "type": "agent_handoff",
                "from_agent": from_name,
                "to_agent": to_agent,
                "summary": summary,
            },
        )

        logger.debug(
            "HandoffTo.run: conv_id=%s from=%s to=%s summary=%r",
            conversation_id,
            from_name,
            to_agent,
            summary,
        )

        return {"status": "handed_off", "to_agent": to_agent, "summary": summary}

    async def run(self, ctx: ToolContext, to_agent: str, summary: str) -> dict:
        """Base run — delegates to _run_handoff. Subclasses override with a typed annotation."""
        return await self._run_handoff(ctx, to_agent, summary)
