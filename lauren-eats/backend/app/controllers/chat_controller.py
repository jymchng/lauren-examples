"""Chat controller — SSE streaming chat with agent handoff.

Follows the chatbot-example pattern:

* ``generate()`` runs the full streaming lifecycle directly — DB setup,
  LLM streaming, DB persistence — so the controller owns the SSE wire.
* A ``try/except/finally`` block inside ``generate()`` ensures that any
  exception yields an ``error`` SSE event and the generator returns
  normally, completing the ASGI response cleanly (no "ASGI callable
  returned without completing response" errors).
* ``ServerSentEvent`` objects are yielded directly; no intermediate
  byte-encoding / re-parsing layer.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import AsyncGenerator

from lauren import (
    EventStream,
    Response,
    ServerSentEvent,
    controller,
    exception_handler,
    post,
    use_exception_handlers,
)
from lauren.types import Request

from app.models.chat import SendChatMessageRequest
from app.services.chat_service import ChatService, _HandoffInfo, _agent_class

logger = logging.getLogger(__name__)


class ChatMessageError(ValueError):
    """Raised when a chat request is malformed (mapped to 400)."""


@exception_handler(ChatMessageError)
class ChatMessageErrorHandler:
    """Maps :class:`ChatMessageError` to a 400 response."""

    async def catch(self, exc: ChatMessageError, request: Request) -> Response:
        logger.info("chat: rejecting malformed request: %s", exc)
        return Response.json({"success": False, "error": str(exc)}, status=400)


@controller("/api/chat", tags=["chat"])
@use_exception_handlers(ChatMessageErrorHandler)
class ChatController:
    def __init__(self, chat_service: ChatService) -> None:
        self._svc = chat_service

    @post("/")
    async def chat(self, body: SendChatMessageRequest) -> EventStream:
        """Stream chat response as SSE.

        Emits the following ``data:`` lines:

        * ``{"type": "meta", "conversationId": "..."}`` — first, always.
        * ``{"id": ..., "choices": [{"delta": {"content": "..."}}]}`` — per token.
        * ``{"type": "handoff", ...}`` — when the agent hands off.
        * ``[DONE]`` — stream complete.
        * (named ``event: error``) — on any exception; lets the ASGI
          response complete cleanly so the client isn't left hanging.
        """
        if not body.message or not body.message.strip():
            raise ChatMessageError("`message` must be a non-empty string")

        message = body.message
        conversation_id = body.conversation_id
        agent_type = body.agent_type

        async def generate() -> AsyncGenerator[ServerSentEvent, None]:
            try:
                conv_id = await self._svc._ensure_conversation(conversation_id, agent_type, message)
                await self._svc._persist_user_message(conv_id, message, agent_type)

                yield ServerSentEvent(data=json.dumps({"type": "meta", "conversationId": conv_id}))

                agent_cls = _agent_class(agent_type)
                runner = await self._svc._runner_for(agent_cls)

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
                        yield ServerSentEvent(data=_sse_delta(chunk.delta))
                    handoff_info.observe(chunk)

                if handoff_info.to_agent:
                    payload = handoff_info.to_sse(agent_type)
                    if payload is not None:
                        yield ServerSentEvent(data=json.dumps(payload))

                await self._svc._persist_assistant_message(conv_id, full_text, agent_type)
                yield ServerSentEvent(data="[DONE]")

            except Exception as exc:
                logger.exception("chat stream error")
                yield ServerSentEvent(event="error", data=str(exc))

        return EventStream(generate(), keep_alive=15.0)


def _sse_delta(delta: str) -> dict:
    """Build an OpenAI-compatible streaming chunk dict for *delta*."""
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion.chunk",
        "choices": [{"delta": {"content": delta}, "index": 0, "finish_reason": None}],
    }
