"""BankingChatController — agentic banking endpoint.

Flow
----
1. Frontend sends ``{ messages, user_id, conversation_id }`` — HMAC-signed.
2. ``SignatureGuard`` verifies the signature AND pins ``request.state.user_id``
   from the now-trusted payload body.
3. Controller reads ``request.state.user_id`` (the guard-verified value, NOT
   the raw body field).
4. If authenticated: looks up account in BankDatabase, enriches request.state,
   prepends [BANKING_AUTH:...] to prompt, routes to AuthenticatedCRMAgent.
5. If not authenticated (no user_id): no auth prefix, routes to
   UnauthenticatedCRMAgent.
6. Wraps the live Request in an ExecutionContext passed to AgentRunner.run().
   This flows AgentContext → ToolContext.execution_context — the security anchor.
7. Runs the active agent and streams SSE.  Agents can hand off; the controller
   loops until the active agent stabilises.

Security guarantees
-------------------
* Identity is pinned to ``request.state`` by ``SignatureGuard`` from a
  body that is cryptographically verified with HMAC-SHA256.
* ``execution_context.request.state.user_id`` holds the guard-verified identity.
* Tools read identity from ``ctx.execution_context.request.state`` — the LLM
  never supplies or influences identity.
"""

from __future__ import annotations

from lauren import EventStream, Json, ServerSentEvent, controller, post, use_guards
from lauren.types import ExecutionContext

from app.ai.agent_names import AUTH_CRM_AGENT_NAME, DISPUTES_AGENT_NAME, TRANSFER_AGENT_NAME, UNAUTH_CRM_AGENT_NAME
from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent
from app.ai.agents.banking_delegation import AuthCRMRunner, DisputesAgentRunner, TransferAgentRunner, UnauthCRMRunner
from app.ai.agents.disputes_agent import DisputesAgent
from app.ai.agents.transfer_agent import BankTransferAgent
from app.ai.agents.unauth_crm_agent import UnauthenticatedCRMAgent
from app.ai.tools.active_agent_store import ActiveAgentStore
from app.banking.bank_db import BankDatabase
from app.ai.chat_schemas import ChatRequest
from app.crypto.authenticated_user_guard import AuthenticatedUserGuard
from app.crypto.signature_guard import SignatureGuard
from app.ws.context import current_user_id
from app.ws.ws_public_token_controller import PUBLIC_WS_USER

_VALID_USERS = frozenset({"alice", "bob", "charlie"})


@use_guards(SignatureGuard)
@controller("/api/banking")
class BankingChatController:
    """Streams banking agent responses as Server-Sent Events.

    Routes each message to the correct agent based on the session's active
    agent (tracked in ``ActiveAgentStore``).  Unauthenticated sessions default
    to ``UnauthenticatedCRMAgent``; authenticated sessions default to
    ``AuthenticatedCRMAgent``.  The active agent changes via HandoffTo tool calls.
    """

    def __init__(
        self,
        unauth_runner: UnauthCRMRunner,
        auth_runner: AuthCRMRunner,
        transfer_runner: TransferAgentRunner,
        disputes_runner: DisputesAgentRunner,
        db: BankDatabase,
        unauth_agent: UnauthenticatedCRMAgent,
        auth_agent: AuthenticatedCRMAgent,
        transfer_agent: BankTransferAgent,
        disputes_agent: DisputesAgent,
        active_agent_store: ActiveAgentStore,
    ) -> None:
        self._db = db
        self._active_agent_store = active_agent_store
        self._agent_registry: dict[str, tuple] = {
            UNAUTH_CRM_AGENT_NAME: (unauth_agent, unauth_runner),
            AUTH_CRM_AGENT_NAME: (auth_agent, auth_runner),
            TRANSFER_AGENT_NAME: (transfer_agent, transfer_runner),
            DISPUTES_AGENT_NAME: (disputes_agent, disputes_runner),
        }
        self._default_unauth = (unauth_agent, unauth_runner)
        self._default_auth = (auth_agent, auth_runner)

    @use_guards(AuthenticatedUserGuard)
    @post("/chat")
    async def stream(self, body: Json[ChatRequest], exec_ctx: ExecutionContext) -> EventStream:
        """Run the active banking agent with verified identity context.

        Event types emitted:
        - ``token``     — text chunk from the model
        - ``tool_use``  — model is invoking a tool; data is the tool name
        - ``break``     — agent handoff; data is the new active agent name
        - ``done``      — end of stream
        - ``error``     — error message
        """
        request = exec_ctx.request
        user_id = (request.state.get("user_id") or body.user_id or "").lower()

        # Reject unknown authenticated users but allow empty user_id (unauthenticated)
        if user_id and user_id not in _VALID_USERS:

            async def _reject():
                yield ServerSentEvent(event="error", data=f"Unknown user: {user_id}")

            return EventStream(_reject())

        if user_id:
            account = self._db.get_account(user_id)
            if not account:

                async def _not_found():
                    yield ServerSentEvent(event="error", data="Account not found")

                return EventStream(_not_found())

            request.state.user_id = account.user_id
            request.state.user_name = account.name
            request.state.account_id = account.account_id
            auth_prefix = (
                f"[BANKING_AUTH: user_id={account.user_id} | name={account.name} | account={account.account_id}]\n\n"
            )
            default_agent = AUTH_CRM_AGENT_NAME
        else:
            account = None
            auth_prefix = ""
            default_agent = UNAUTH_CRM_AGENT_NAME

        user_messages = [m for m in body.messages if m.role == "user"]
        raw_message = user_messages[-1].content if user_messages else ""
        full_prompt = auth_prefix + raw_message

        def _resolve_agent(active: str):
            if user_id:
                fallback = self._default_auth
            else:
                fallback = self._default_unauth
            return self._agent_registry.get(active, fallback)

        # Set the WS routing context BEFORE returning EventStream — the
        # handler's task must hold this var so every __anext__() task
        # spawned by EventStream's framing loop inherits a copy via PEP
        # 567 context copy.  Setting it inside the async generator only
        # affects the first __anext__() task; subsequent chunk advances
        # would see ``None`` and the EventForwarder signal handlers
        # would early-return without forwarding to the WebSocket.
        if user_id:
            current_user_id.set(user_id)

        async def generate():
            try:
                conv_id = body.conversation_id
                max_handoffs = 8

                active = self._active_agent_store.get(conv_id, default_agent)
                prompt = full_prompt
                handoffs = 0

                while True:
                    agent, runner = _resolve_agent(active)

                    seen_tool_uses: set[str] = set()
                    async for chunk in await runner.run_stream(
                        agent,
                        prompt,
                        conversation_id=f"{conv_id}:{active}",
                        execution_context=exec_ctx,
                        metadata={"conversation_id": conv_id},
                    ):
                        if chunk.delta:
                            yield ServerSentEvent(event="token", data=chunk.delta)
                        elif chunk.tool_call_delta is not None:
                            tcd = chunk.tool_call_delta
                            if tcd.name and tcd.tool_use_id not in seen_tool_uses:
                                seen_tool_uses.add(tcd.tool_use_id)
                                yield ServerSentEvent(event="tool_use", data=tcd.name)

                    new_active = self._active_agent_store.get(conv_id, default_agent)
                    if new_active == active or handoffs >= max_handoffs:
                        break

                    handoffs += 1
                    summary = self._active_agent_store.pop_pending_summary(conv_id)
                    yield ServerSentEvent(event="break", data=new_active)

                    if summary:
                        prompt = (
                            auth_prefix
                            + f"[HANDOFF from {active}]: {summary}\n\n"
                            + f"[ORIGINAL REQUEST]: {raw_message}"
                        )
                    else:
                        prompt = full_prompt
                    active = new_active

                yield ServerSentEvent(event="done", data="")
            except Exception as exc:
                yield ServerSentEvent(event="error", data=str(exc))

        return EventStream(generate(), keep_alive=15.0)

    @post("/chat/public")
    async def stream_public(self, body: Json[ChatRequest], exec_ctx: ExecutionContext) -> EventStream:
        """Public (unauthenticated) chat — routes only to UnauthenticatedCRMAgent.

        Event types emitted: ``token``, ``tool_use``, ``break``, ``done``, ``error``.
        No user_id is required; WS events are forwarded via the ``__public__`` channel.
        """
        conv_id = body.conversation_id
        user_messages = [m for m in body.messages if m.role == "user"]
        raw_message = user_messages[-1].content if user_messages else ""

        # Set on the handler task before returning EventStream — see the
        # comment in stream() for why this MUST NOT live inside generate().
        current_user_id.set(PUBLIC_WS_USER)

        async def generate():
            try:
                active = self._active_agent_store.get(conv_id, UNAUTH_CRM_AGENT_NAME)
                prompt = raw_message
                handoffs = 0
                max_handoffs = 4

                while True:
                    agent, runner = self._agent_registry.get(active, self._default_unauth)

                    seen_tool_uses: set[str] = set()
                    async for chunk in await runner.run_stream(
                        agent,
                        prompt,
                        conversation_id=f"{conv_id}:{active}",
                        execution_context=exec_ctx,
                        metadata={"conversation_id": conv_id},
                    ):
                        if chunk.delta:
                            yield ServerSentEvent(event="token", data=chunk.delta)
                        elif chunk.tool_call_delta is not None:
                            tcd = chunk.tool_call_delta
                            if tcd.name and tcd.tool_use_id not in seen_tool_uses:
                                seen_tool_uses.add(tcd.tool_use_id)
                                yield ServerSentEvent(event="tool_use", data=tcd.name)

                    new_active = self._active_agent_store.get(conv_id, UNAUTH_CRM_AGENT_NAME)
                    if new_active == active or handoffs >= max_handoffs:
                        break

                    handoffs += 1
                    summary = self._active_agent_store.pop_pending_summary(conv_id)
                    yield ServerSentEvent(event="break", data=new_active)
                    prompt = summary or raw_message
                    active = new_active

                yield ServerSentEvent(event="done", data="")
            except Exception as exc:
                yield ServerSentEvent(event="error", data=str(exc))

        return EventStream(generate(), keep_alive=15.0)
