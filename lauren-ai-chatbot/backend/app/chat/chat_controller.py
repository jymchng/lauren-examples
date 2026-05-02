"""ChatController — the streaming AI chat endpoint.

Architecture highlights
-----------------------
* ``@use_guards(SignatureGuard)`` — every route in this controller is
  protected: the guard verifies the HMAC-SHA256 ``X-Signature`` header
  before the handler runs.
* ``Json[ChatRequest]`` — Lauren's built-in JSON body extractor; it
  parses and validates the request body with Pydantic.  Because the guard
  already called ``request.body()`` to verify the signature, Lauren returns
  the cached bytes here — the body is NOT re-read from the socket.
* The handler returns an ``EventStream`` so tokens stream to the browser
  as they arrive from OpenRouter.
* ``keep_alive=15.0`` emits a comment frame every 15 s to prevent
  load-balancers from killing idle connections.

Layout::

    POST /api/chat/  ──▶  SignatureGuard  ──▶  ChatController.stream
                                                     │
                                              ChatService.stream_tokens
                                                     │
                                              EventStream (SSE)  ──▶  browser
"""

from lauren import (
    EventStream,
    Json,
    ServerSentEvent,
    controller,
    post,
    use_guards,
)

from app.chat.chat_service import ChatService
from app.chat.schemas import ChatRequest
from app.crypto.signature_guard import SignatureGuard


@use_guards(SignatureGuard)
@controller("/api/chat")
class ChatController:
    def __init__(self, chat_service: ChatService) -> None:
        self._chat_service = chat_service

    @post("/")
    async def stream(self, body: Json[ChatRequest]) -> EventStream:
        """Stream AI tokens as Server-Sent Events.

        Event types emitted:
        - ``token``  — a text chunk from the model (``data`` = the token)
        - ``done``   — signals end of stream (``data`` = ``""`` )
        - ``error``  — something went wrong upstream (``data`` = message)
        """

        async def generate():
            try:
                async for token in self._chat_service.stream_tokens(body):
                    yield ServerSentEvent(event="token", data=token)
                yield ServerSentEvent(event="done", data="")
            except Exception as exc:
                yield ServerSentEvent(event="error", data=str(exc))

        return EventStream(generate(), keep_alive=15.0)
