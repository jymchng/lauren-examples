"""AgentController — general-purpose chat endpoint proxied via /api/chat on the frontend.

Flow
----
1. Frontend's /api/chat route signs the payload and POSTs to /api/agent/.
2. ``SignatureGuard`` verifies the HMAC signature and pins ``user_id`` from
   the verified body to ``request.state``.
3. Controller falls back to ``user_id = "alice"`` (the schema default) when no
   user_id is provided, so the demo works without authentication setup.
4. Runs ``BankingCRMAgent`` and streams the response as SSE.

This mirrors ``BankingChatController`` but lives at a simpler path for
frontends that don't yet use the banking-specific multi-user flow.
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
@controller("/api/agent")
class AgentController:
    """General agent chat endpoint — streams BankingCRMAgent responses as SSE."""

    def __init__(
        self,
        runner: AgentRunner,
        db: BankDatabase,
        crm: BankingCRMAgent,
    ) -> None:
        self._runner = runner
        self._db = db
        self._crm = crm

    @post("/")
    async def stream(self, body: Json[ChatRequest], request: Request) -> EventStream:
        """Run the BankingCRMAgent.

        Event types emitted:
        - ``token``  — text chunk from the model
        - ``done``   — end of stream
        - ``error``  — error message
        """
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
            f"[BANKING_AUTH: user_id={account.user_id} | "
            f"name={account.name} | "
            f"account={account.account_id}]\n\n"
        )
        full_prompt = auth_prefix + raw_message
        exec_ctx = ExecutionContext(request=request)

        async def generate():
            try:
                response = await self._runner.run(
                    self._crm,
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
