"""AgentController — agentic chat endpoint with tool use.

Architecture highlights
-----------------------
* ``@use_guards(SignatureGuard)`` — same HMAC-SHA256 guard as the regular chat
  endpoint.
* Resolves the ``ChatAgent`` from the DI container via the ``Agent[ChatAgent]``
  extractor and the ``AgentRunner`` singleton, then runs the agent through the
  agentic loop.
* Returns an ``EventStream`` so the frontend receives the same SSE wire format
  as the regular chat endpoint.

Layout::

    POST /api/agent/  ──▶  SignatureGuard  ──▶  AgentController.stream
                                                       │
                                               AgentRunner.run(ChatAgent, ...)
                                                       │
                                               EventStream (SSE)  ──▶  browser
"""

from __future__ import annotations

from lauren import (
    EventStream,
    Json,
    ServerSentEvent,
    controller,
    post,
    use_guards,
)
from lauren_ai import AgentRunner

from app.ai.orchestrator_agent import OrchestratorAgent
from app.chat.schemas import ChatRequest
from app.crypto.signature_guard import SignatureGuard


@use_guards(SignatureGuard)
@controller("/api/agent")
class AgentController:
    """Streams agentic responses (with tool use and delegation) as Server-Sent Events."""

    def __init__(self, runner: AgentRunner) -> None:
        self._runner = runner

    @post("/")
    async def stream(self, body: Json[ChatRequest]) -> EventStream:
        """Run OrchestratorAgent and stream the response as Server-Sent Events.

        The OrchestratorAgent routes requests to specialist sub-agents:
        - Research / URL fetching  → ResearchAgent
        - Code execution / maths   → CodeAssistantAgent
        - General questions         → answered directly

        Event types emitted:
        - ``token``  — a text chunk from the model (``data`` = the token)
        - ``done``   — signals end of stream (``data`` = ``""`` )
        - ``error``  — something went wrong (``data`` = message)
        """
        # Extract the last user message as the prompt for the agent.
        user_messages = [m for m in body.messages if m.role == "user"]
        prompt = user_messages[-1].content if user_messages else ""

        async def generate():
            try:
                response = await self._runner.run(
                    OrchestratorAgent,
                    prompt,
                    conversation_id=body.conversation_id,
                )
                content = response.content
                if content:
                    chunk_size = 50
                    for i in range(0, len(content), chunk_size):
                        yield ServerSentEvent(event="token", data=content[i : i + chunk_size])
                yield ServerSentEvent(event="done", data="")
            except Exception as exc:
                yield ServerSentEvent(event="error", data=str(exc))

        return EventStream(generate(), keep_alive=15.0)
