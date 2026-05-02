"""TeamController — multi-agent team endpoint.

Architecture highlights
-----------------------
* ``@use_guards(SignatureGuard)`` — same HMAC-SHA256 guard as the other chat
  endpoints.
* Receives ``TeamRunner`` via DI.
* Streams distinct SSE event types so the frontend can render step-by-step
  team progress.

Event types emitted::

    event: worker_started   data: {"worker": name, "round": n}
    event: worker_finished  data: {"worker": name, "preview": ..., "round": n}
    event: coordinator      data: decision string
    event: team_done        data: final answer string
    event: done             data: ""  (closes the stream)
    event: error            data: error message string
"""

from __future__ import annotations

import json

from lauren import (
    EventStream,
    Json,
    ServerSentEvent,
    controller,
    post,
    use_guards,
)
from lauren_ai import TeamCoordinatorDecision, TeamFinalAnswer, TeamRunner, TeamWorkerFinished, TeamWorkerStarted

from app.crypto.signature_guard import SignatureGuard
from app.team.team_schemas import TeamRequest


@use_guards(SignatureGuard)
@controller("/api/team")
class TeamController:
    """Streams multi-agent team execution events as Server-Sent Events."""

    def __init__(self, runner: TeamRunner) -> None:
        self._runner = runner

    @post("/")
    async def stream(self, body: Json[TeamRequest]) -> EventStream:
        """Run the ResearchTeam and stream progress as Server-Sent Events.

        Event types emitted:
        - ``worker_started``  — a worker agent begins a sub-task
        - ``worker_finished`` — a worker agent completes a sub-task
        - ``coordinator``     — the coordinator makes a routing decision
        - ``team_done``       — final answer is ready
        - ``done``            — stream is closed
        - ``error``           — something went wrong
        """
        async def generate():
            try:
                async for event in self._runner.run_stream(
                    body.task,
                    conversation_id=body.conversation_id,
                ):
                    if isinstance(event, TeamWorkerStarted):
                        yield ServerSentEvent(
                            event="worker_started",
                            data=json.dumps({
                                "worker": event.worker_name,
                                "round": event.round,
                            }),
                        )
                    elif isinstance(event, TeamWorkerFinished):
                        yield ServerSentEvent(
                            event="worker_finished",
                            data=json.dumps({
                                "worker": event.worker_name,
                                "preview": event.result_content[:200],
                                "round": event.round,
                            }),
                        )
                    elif isinstance(event, TeamCoordinatorDecision):
                        yield ServerSentEvent(
                            event="coordinator",
                            data=event.decision,
                        )
                    elif isinstance(event, TeamFinalAnswer):
                        yield ServerSentEvent(
                            event="team_done",
                            data=event.content,
                        )
                yield ServerSentEvent(event="done", data="")
            except Exception as exc:
                yield ServerSentEvent(event="error", data=str(exc))

        return EventStream(generate(), keep_alive=30.0)
