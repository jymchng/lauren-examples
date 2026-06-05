"""Chat controller — SSE streaming chat with agent handoff.

P0 fix (issue 5.1): the controller used to mix business logic with
``ctx.response`` plumbing and try/except blocks.  It now delegates the
streaming to :class:`ChatService` and uses an :func:`@exception_handler`
to translate domain errors into 4xx responses.
"""

from __future__ import annotations

import logging
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
from app.services.chat_service import ChatService

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

        Body is parsed into a :class:`SendChatMessageRequest` Pydantic
        model via the framework's ``Json[T]`` extractor (issue 4.7).
        The model is *not* an orphan anymore — every controller that
        accepts a JSON body now uses a typed schema.
        """
        if not body.message or not body.message.strip():
            raise ChatMessageError("`message` must be a non-empty string")

        async def generate() -> AsyncGenerator[ServerSentEvent, None]:
            async for chunk in self._svc.stream_chat(
                message=body.message,
                conversation_id=body.conversation_id,
                agent_type=body.agent_type,
            ):
                text = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
                for line in text.strip().split("\n\n"):
                    if line.startswith("data: "):
                        yield ServerSentEvent(data=line[6:])

        return EventStream(generate(), keep_alive=15.0)
