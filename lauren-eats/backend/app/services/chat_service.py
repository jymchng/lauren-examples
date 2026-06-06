"""Chat service — SSE streaming chat driven by ``AgentRunner``.

P0 fixes (all chat-related):
- Issue 9.3: no more hand-rolled ``httpx`` call.  The service now resolves
  ``LLMService`` and ``AgentRunner[ConciergeAgent]`` from the DI graph
  and forwards the user's message to the runner.
- Issue 10.3: ``runner.run_stream`` is the actual entry point.  The
  runner handles tools, handoffs, and signals itself.
- Issue 12.1: handoff is now an explicit tool call emitted by the agent;
  the regex-based ``<<HANDOFF:...>>`` extraction is gone.
- Issue 10.6: the agent's own system prompt is used (no override in
  ``chat_service``).

The service still owns:

* Conversation persistence (the ``conversations`` and ``agent_messages``
  tables) — these are application concerns, not LLM concerns.
* The SSE wire format — the controller maps
  ``CompletionChunk.delta`` into a ``ServerSentEvent``.

Non-streaming callers (tests, future REST endpoints) can use
:meth:`complete` for a one-shot response.
"""

from __future__ import annotations

import json
import uuid
from typing import AsyncGenerator

from lauren import Scope, injectable
from lauren_ai import AgentRunner, Message
from lauren_ai._transport import CompletionChunk

from app.agents.concierge import ConciergeAgent
from app.db.database import DatabaseService

# Lazy import to avoid a circular dependency between chat_service and
# the agents module.
_AGENT_CLASS_MAP: dict[str, type] = {}


def _agent_class(agent_type: str | None) -> type:
    """Return the ``@agent``-decorated class for *agent_type*.

    Falls back to :class:`ConciergeAgent` when the type is unknown or
    absent.  Imports are lazy so this module remains importable in
    environments where the agents module is not yet resolved.
    """
    if not _AGENT_CLASS_MAP:
        from app.agents.concierge import ConciergeAgent
        from app.agents.dietary import DietaryAgent
        from app.agents.food_recommender import FoodRecommenderAgent
        from app.agents.ordering_agent import OrderingAgent
        from app.agents.reservation_agent import ReservationAgent
        from app.agents.support import SupportAgent

        _AGENT_CLASS_MAP.update(
            {
                "concierge": ConciergeAgent,
                "food_recommender": FoodRecommenderAgent,
                "dietary": DietaryAgent,
                "ordering": OrderingAgent,
                "reservation": ReservationAgent,
                "support": SupportAgent,
            }
        )
    return _AGENT_CLASS_MAP.get(agent_type or "concierge", _AGENT_CLASS_MAP["concierge"])


def _new_id() -> str:
    return uuid.uuid4().hex[:25]


@injectable(scope=Scope.SINGLETON)
class ChatService:
    """High-level chat service used by the :class:`ChatController`."""

    def __init__(
        self,
        db: DatabaseService,
        concierge_runner: AgentRunner[ConciergeAgent],
    ) -> None:
        self._db = db
        self._concierge_runner = concierge_runner

    async def _ensure_conversation(
        self,
        conversation_id: str | None,
        agent_type: str | None,
        first_message: str,
    ) -> str:
        if conversation_id:
            existing = await self._db.fetch_one(
                "SELECT id FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            if existing is not None:
                return conversation_id
        conv_id = conversation_id or _new_id()
        # Upsert — if the caller sent a fresh id, also create the row.
        await self._db.execute(
            "INSERT OR IGNORE INTO conversations (id, agent_type, title, status) "
            "VALUES (?, ?, ?, 'active')",
            (conv_id, agent_type, first_message[:50]),
        )
        return conv_id

    async def _persist_user_message(
        self,
        conversation_id: str,
        message: str,
        agent_type: str | None,
    ) -> None:
        await self._db.execute(
            "INSERT INTO agent_messages (id, conversation_id, role, content, agent_type) "
            "VALUES (?, ?, 'user', ?, ?)",
            (_new_id(), conversation_id, message, agent_type),
        )

    async def _persist_assistant_message(
        self,
        conversation_id: str,
        content: str,
        agent_type: str | None,
    ) -> None:
        await self._db.execute(
            "INSERT INTO agent_messages (id, conversation_id, role, content, agent_type) "
            "VALUES (?, ?, 'assistant', ?, ?)",
            (_new_id(), conversation_id, content, agent_type),
        )
        await self._db.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )

    async def _load_history(self, conversation_id: str, limit: int = 20) -> list[Message]:
        rows = await self._db.fetch_all(
            "SELECT role, content FROM agent_messages "
            "WHERE conversation_id = ? AND role IN ('user', 'assistant') "
            "ORDER BY created_at ASC LIMIT ?",
            (conversation_id, limit),
        )
        return [Message(role=row["role"], content=row["content"]) for row in rows]

    async def complete(
        self,
        message: str,
        *,
        conversation_id: str | None = None,
        agent_type: str | None = None,
    ) -> str:
        """Run a one-shot chat completion and return the final text.

        Used by tests and any non-streaming caller.
        """
        conv_id = await self._ensure_conversation(conversation_id, agent_type, message)
        await self._persist_user_message(conv_id, message, agent_type)

        history = await self._load_history(conv_id)
        # ``history`` already includes the user message we just persisted;
        # the runner takes only the *new* message, so drop the tail.
        if history and history[-1].content == message:
            history = history[:-1]

        agent_cls = _agent_class(agent_type)
        runner = await self._runner_for(agent_cls)
        final_text = ""
        stream = await runner.run_stream(
            agent_cls(),
            message,
            conversation_id=conv_id,
            metadata={"conversation_id": conv_id},
        )
        async for chunk in stream:
            final_text += chunk.delta
        await self._persist_assistant_message(conv_id, final_text, agent_type)
        return final_text

    async def stream_chat(
        self,
        message: str,
        *,
        conversation_id: str | None = None,
        agent_type: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        """Stream chat response as SSE events.

        Yields ``bytes`` lines of the form ``data: {json}\\n\\n`` followed
        by a final ``data: [DONE]\\n\\n``.  The :class:`ChatController`
        re-encodes these as ``ServerSentEvent`` objects.
        """
        conv_id = await self._ensure_conversation(conversation_id, agent_type, message)
        await self._persist_user_message(conv_id, message, agent_type)

        history = await self._load_history(conv_id)
        if history and history[-1].content == message:
            history = history[:-1]

        # Emit the meta event with the conversation id immediately.
        yield f"data: {json.dumps({'type': 'meta', 'conversationId': conv_id})}\n\n".encode()

        agent_cls = _agent_class(agent_type)
        runner = await self._runner_for(agent_cls)
        full_text = ""
        handoff_info = _HandoffInfo()
        stream = await runner.run_stream(
            agent_cls(),
            message,
            conversation_id=conv_id,
            metadata={"conversation_id": conv_id},
        )
        async for chunk in stream:
            if chunk.delta:
                full_text += chunk.delta
                yield _sse_chunk(chunk.delta)
            handoff_info.observe(chunk)

        # If the agent used the HandoffTo tool, emit a handoff SSE event
        # so the frontend can switch the active agent display and show a
        # transfer message.  The framework's runner updates the active
        # agent in the conversation row; we just mirror that to the wire.
        if handoff_info.to_agent:
            payload = handoff_info.to_sse(agent_type)
            if payload is not None:
                yield f"data: {json.dumps(payload)}\n\n".encode()

        await self._persist_assistant_message(conv_id, full_text, agent_type)
        yield b"data: [DONE]\n\n"

    async def _runner_for(self, agent_cls: type):
        """Return the per-agent ``AgentRunner`` for *agent_cls*.

        The concierge runner is held in a constructor-injected slot for
        the common case.  Other agents are resolved by the framework on
        demand — see :func:`app.services.runner_resolver.resolve_runner`.
        """
        if agent_cls is ConciergeAgent:
            return self._concierge_runner
        # Lazy import: avoid a hard dependency on the app module
        # graph at construction time (which would create a cycle).
        from app.services.runner_resolver import resolve_runner

        return await resolve_runner(agent_cls)


def _sse_chunk(delta: str) -> bytes:
    """Encode *delta* as a single OpenAI-compatible SSE chunk."""
    payload = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion.chunk",
        "choices": [{"delta": {"content": delta}, "index": 0, "finish_reason": None}],
    }
    return f"data: {json.dumps(payload)}\n\n".encode()


class _HandoffInfo:
    """Accumulates :class:`ToolCallDelta` chunks to detect a ``HandoffTo`` call.

    The streaming transport delivers tool calls as a sequence of
    ``tool_call_delta`` chunks — first the tool name, then partial JSON
    fragments.  We collect the fragments until the call completes, then
    attempt to parse out the ``to_agent`` field.

    Display-name → agent-type lookup mirrors ``HandoffTo._by_name`` so the
    SSE event mirrors what the frontend's existing handoff handler expects.
    """

    _DISPLAY_NAMES: dict[str, str] = {
        "concierge": "Concierge",
        "food_recommender": "Food Expert",
        "dietary": "Dietary Guide",
        "ordering": "Order Assistant",
        "reservation": "Reservation Desk",
        "support": "Support",
    }
    _AGENT_EMOJI: dict[str, str] = {
        "concierge": "🎩",
        "food_recommender": "🍜",
        "dietary": "🥬",
        "ordering": "🛒",
        "reservation": "📅",
        "support": "🛟",
    }
    _BY_DISPLAY: dict[str, str] = {v: k for k, v in _DISPLAY_NAMES.items()}

    def __init__(self) -> None:
        self._buffer: str = ""
        self._saw_handoff: bool = False
        self.to_agent: str | None = None

    def observe(self, chunk) -> None:
        tcd = chunk.tool_call_delta
        if tcd is None:
            return
        if tcd.name == "HandoffTo" and not self._saw_handoff:
            self._saw_handoff = True
        if self._saw_handoff and tcd.input_delta:
            self._buffer += tcd.input_delta
            try:
                parsed = json.loads(self._buffer)
            except json.JSONDecodeError:
                return
            target = parsed.get("to_agent")
            if isinstance(target, str) and target in self._DISPLAY_NAMES.values():
                self.to_agent = target

    def to_sse(self, from_agent: str | None) -> dict | None:
        """Build a ``type: 'handoff'`` SSE payload mirroring the frontend's schema."""
        from_key = from_agent or "concierge"
        to_display = self.to_agent
        if to_display is None:
            return None
        return {
            "type": "handoff",
            "fromAgent": from_key,
            "toAgent": self._BY_DISPLAY[to_display],
            "fromAgentName": self._DISPLAY_NAMES.get(from_key, "Assistant"),
            "toAgentName": to_display,
            "fromAgentEmoji": self._AGENT_EMOJI.get(from_key, "🤖"),
            "toAgentEmoji": self._AGENT_EMOJI.get(self._BY_DISPLAY[to_display], "🤖"),
            "reason": f"Transferring you to {to_display}",
        }
