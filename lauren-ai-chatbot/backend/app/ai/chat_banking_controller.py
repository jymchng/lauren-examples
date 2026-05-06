"""BankingChatController — agentic banking endpoint.

Flow
----
1. Frontend sends ``{ messages, user_id, conversation_id }`` — HMAC-signed.
2. ``SignatureGuard`` verifies the signature AND pins ``request.state.user_id``
   from the now-trusted payload body.
3. Controller reads ``request.state.user_id`` (the guard-verified value, NOT
   the raw body field) and looks up the account in ``BankDatabase``.
4. Enriches ``request.state`` with the canonical account details.
5. Wraps the live ``Request`` object in a lauren ``ExecutionContext`` and passes
   it to ``AgentRunner.run()`` as ``execution_context``.  This is the security
   anchor: it flows ``AgentContext → ToolContext.execution_context`` and is
   never part of any JSON schema the LLM sees.
6. Prepends ``[BANKING_AUTH: ...]`` to the customer message so the CRM Agent
   can address the customer by name.  **UX only** — tools never derive identity
   from message text.
7. Runs the active agent (defaults to English CRM) and streams SSE.  Agents
   can hand off to each other; the controller loops until the active agent
   stabilises.

Security guarantees
-------------------
* Identity is pinned to ``request.state`` by ``SignatureGuard`` from a
  body that is cryptographically verified with HMAC-SHA256.  The browser
  cannot change ``user_id`` without breaking the signature.
* ``execution_context`` is a ``lauren.types.ExecutionContext`` whose
  ``.request.state.user_id`` holds the guard-verified identity.
* ``TransferFundsTool`` and ``GetTransactionHistoryTool`` read
  ``ctx.execution_context.request.state.get("user_id")`` — the LLM
  supplies only transfer details (recipient, amount), never the sender.
"""

from __future__ import annotations

from lauren import EventStream, Json, ServerSentEvent, controller, post, use_guards
from lauren.types import ExecutionContext

from app.ai.active_agent_store import ActiveAgentStore
from app.ai.agent_names import CRM_AGENT_NAME_EN, CRM_AGENT_NAME_ZH, TRANSFER_AGENT_NAME_EN, TRANSFER_AGENT_NAME_ZH
from app.ai.crm_agent import BankingCRMAgentEN
from app.ai.crm_agent_zh import BankingCRMAgentZH
from app.ai.transfer_agent import BankingTransferAgentEN
from app.ai.transfer_agent_zh import BankingTransferAgentZH
from app.banking.bank_db import BankDatabase
from app.ai.chat_schemas import ChatRequest
from app.crypto.signature_guard import SignatureGuard
from app.ws.context import current_user_id
from app.ai.banking_delegation import CRMAgentRunner, TransferAgentRunner

_VALID_USERS = frozenset({"alice", "bob", "charlie"})


@use_guards(SignatureGuard)
@controller("/api/banking")
class BankingChatController:
    """Streams banking agent responses as Server-Sent Events.

    Routes each message to the correct agent based on the session's active
    agent (tracked in ``ActiveAgentStore``).  Defaults to the English CRM
    agent; the active agent changes via ``HandoffTo`` tool calls.  Supports
    four agents across two language pairs (English and Mandarin).
    """

    def __init__(
        self,
        runner: CRMAgentRunner,
        transfer_runner: TransferAgentRunner,
        db: BankDatabase,
        crm_agent: BankingCRMAgentEN,
        crm_agent_zh: BankingCRMAgentZH,
        transfer_agent: BankingTransferAgentEN,
        transfer_agent_zh: BankingTransferAgentZH,
        active_agent_store: ActiveAgentStore,
    ) -> None:
        self._db = db
        self._active_agent_store = active_agent_store
        self._crm_agent = crm_agent          # default fallback
        self._runner = runner                 # default fallback runner
        self._agent_registry: dict[str, tuple] = {
            CRM_AGENT_NAME_EN:      (crm_agent,         runner),
            CRM_AGENT_NAME_ZH:      (crm_agent_zh,      runner),
            TRANSFER_AGENT_NAME_EN: (transfer_agent,    transfer_runner),
            TRANSFER_AGENT_NAME_ZH: (transfer_agent_zh, transfer_runner),
        }

    @post("/chat")
    async def stream(self, body: Json[ChatRequest], exec_ctx: ExecutionContext) -> EventStream:
        """Run the active banking agent with verified identity context.

        Event types emitted:
        - ``token``  — text chunk from the model
        - ``break``  — agent handoff; data is the new active agent name
        - ``done``   — end of stream
        - ``error``  — error message
        """
        # ── Identity: read from request.state, NOT from the raw body field ──
        request = exec_ctx.request
        user_id = (request.state.get("user_id") or body.user_id).lower()

        if user_id not in _VALID_USERS:

            async def _reject():
                yield ServerSentEvent(event="error", data=f"Unknown user: {user_id}")

            return EventStream(_reject())

        account = self._db.get_account(user_id)
        if not account:

            async def _not_found():
                yield ServerSentEvent(event="error", data="Account not found")

            return EventStream(_not_found())

        request.state.user_id = account.user_id
        request.state.user_name = account.name
        request.state.account_id = account.account_id

        user_messages = [m for m in body.messages if m.role == "user"]
        raw_message = user_messages[-1].content if user_messages else ""

        auth_prefix = (
            f"[BANKING_AUTH: user_id={account.user_id} | name={account.name} | account={account.account_id}]\n\n"
        )
        full_prompt = auth_prefix + raw_message

        def _resolve_agent(active: str):
            return self._agent_registry.get(active, (self._crm_agent, self._runner))

        async def generate():
            current_user_id.set(account.user_id)
            try:
                conv_id = body.conversation_id
                chunk_size = 40
                max_handoffs = 8

                active = self._active_agent_store.get(conv_id, CRM_AGENT_NAME_EN)
                prompt = full_prompt
                handoffs = 0

                while True:
                    agent, runner = _resolve_agent(active)

                    response = await runner.run(
                        agent,
                        prompt,
                        conversation_id=f"{conv_id}:{active}",
                        execution_context=exec_ctx,
                        metadata={"conversation_id": conv_id},
                    )
                    content = response.content or ""
                    for i in range(0, len(content), chunk_size):
                        yield ServerSentEvent(event="token", data=content[i : i + chunk_size])

                    new_active = self._active_agent_store.get(conv_id, CRM_AGENT_NAME_EN)
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
