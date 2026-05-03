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
7. Runs ``BankingCRMAgent`` and streams the response as SSE.

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
* If ``execution_context.request.state.user_id`` does not match what the
  LLM tried to pass as a parameter, the tool rejects the call as a
  potential prompt-injection attack.
"""

from __future__ import annotations

from lauren import EventStream, Json, Request, ServerSentEvent, controller, post, use_guards
from lauren.types import ExecutionContext
from lauren_ai import AgentRunner

from app.ai.crm_agent import BankingCRMAgent
from app.banking.bank_db import BankDatabase
from app.chat.schemas import ChatRequest
from app.crypto.signature_guard import SignatureGuard

_VALID_USERS = frozenset({"alice", "bob", "charlie"})


@use_guards(SignatureGuard)
@controller("/api/banking")
class BankingChatController:
    """Streams banking CRM agent responses as Server-Sent Events."""

    def __init__(
        self,
        runner: AgentRunner,
        db: BankDatabase,
    ) -> None:
        self._runner = runner
        self._db = db

    @post("/chat")
    async def stream(self, body: Json[ChatRequest], request: Request) -> EventStream:
        """Run the BankingCRMAgent with verified identity context.

        Event types emitted:
        - ``token``  — text chunk from the model
        - ``done``   — end of stream
        - ``error``  — error message
        """
        # ── Identity: read from request.state, NOT from the raw body field ──
        # SignatureGuard already verified the HMAC and stored the user_id from
        # the signed payload.  We trust state, not the parsed body value.
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

        # Enrich request.state with the canonical account details so tools
        # can access them without another DB round-trip.
        request.state.user_id = account.user_id
        request.state.user_name = account.name
        request.state.account_id = account.account_id

        # Extract the customer's last user message
        user_messages = [m for m in body.messages if m.role == "user"]
        raw_message = user_messages[-1].content if user_messages else ""

        # UX-only identity tag — lets the CRM Agent address the customer by
        # name.  Tools MUST NOT use this for authorisation; they read from
        # execution_context.request.state instead.
        auth_prefix = (
            f"[BANKING_AUTH: user_id={account.user_id} | "
            f"name={account.name} | "
            f"account={account.account_id}]\n\n"
        )
        full_prompt = auth_prefix + raw_message

        # Wrap the request in a real lauren ExecutionContext so the chain
        #   AgentRunner → AgentContext → ToolContext.execution_context
        # carries a proper ExecutionContext whose .request.state holds the
        # guard-verified identity — not a plain dict that could drift.
        exec_ctx = ExecutionContext(request=request)

        async def generate():
            try:
                response = await self._runner.run(
                    BankingCRMAgent,
                    full_prompt,
                    conversation_id=body.conversation_id,
                    execution_context=exec_ctx,
                )
                content = response.content or ""
                chunk_size = 40
                for i in range(0, len(content), chunk_size):
                    yield ServerSentEvent(event="token", data=content[i : i + chunk_size])
                yield ServerSentEvent(event="done", data="")
            except Exception as exc:
                yield ServerSentEvent(event="error", data=str(exc))

        return EventStream(generate(), keep_alive=15.0)
