"""ChatService — streams completions via ``lauren-ai`` LLMService.

Delegates all LLM communication to :class:`~lauren_ai._module.LLMService`,
which is configured in ``AIModule`` and provided to this service via DI.

When ``conversation_id`` is set on the request, the service loads previous
messages from an in-process :class:`~lauren_ai._memory._stores.InMemoryConversationStore`
and appends the new exchange before saving.  This gives the chatbot
persistent memory across requests within a single process lifetime.

The service remains a SINGLETON so the conversation store is shared across
all requests in the same process.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from lauren import Scope, injectable
from lauren_ai import InMemoryConversationStore
from lauren_ai._module import LLMService
from lauren_ai._transport import Message as LLMMessage

from app.chat.schemas import ChatRequest

logger = logging.getLogger(__name__)


@injectable(scope=Scope.SINGLETON)
class ChatService:
    """Streams tokens from the configured LLM provider via LLMService.

    Delegates to ``LLMService.complete_stream()`` for streaming completions.
    When the request carries a ``conversation_id`` the full conversation
    history is loaded before the call, the new messages are prepended, and
    the updated history (including the assistant reply) is saved back to the
    in-memory store after streaming completes.
    """

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service
        self._store = InMemoryConversationStore()

    async def stream_tokens(self, request: ChatRequest) -> AsyncIterator[str]:
        """Yield individual text tokens from the LLM streaming response.

        Loads conversation history when ``request.conversation_id`` is set,
        prepends it to the current messages, and saves the full updated
        history (including the assistant reply) after the stream completes.
        """
        # Convert app schema messages → lauren_ai transport messages.
        # Filter system messages out (transport Message only accepts user/assistant).
        new_messages: list[LLMMessage] = [
            LLMMessage(role=m.role, content=m.content)  # type: ignore[arg-type]
            for m in request.messages
            if m.role in ("user", "assistant")
        ]

        # Load prior history if a conversation_id is provided.
        history: list[LLMMessage] = []
        if request.conversation_id:
            raw = await self._store.load(request.conversation_id)
            history = [
                LLMMessage(role=entry["role"], content=entry["content"])
                for entry in raw
                if entry.get("role") in ("user", "assistant")
            ]

        all_messages = history + new_messages

        # Stream tokens and collect the full assistant reply.
        collected: list[str] = []
        stream = await self._llm.complete_stream(
            all_messages,
            model=request.model,
        )
        async for chunk in stream:
            if chunk.delta:
                collected.append(chunk.delta)
                yield chunk.delta

        # Persist updated history when a conversation_id was supplied.
        if request.conversation_id:
            assistant_reply = "".join(collected)
            updated: list[dict[str, str]] = [
                {"role": str(m.role), "content": str(m.content) if isinstance(m.content, str) else ""}
                for m in all_messages
            ]
            updated.append({"role": "assistant", "content": assistant_reply})
            await self._store.save(request.conversation_id, updated)
