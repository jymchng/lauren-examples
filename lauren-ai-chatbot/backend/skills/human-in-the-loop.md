# Human-in-the-Loop Transfer Approval

## Contents
- Flow overview
- ApprovalService — asyncio.Future registry
- ApprovalTool — agent-side gate
- ApprovalController — browser endpoint
- One-shot transfer token consumed by TransferFundsTool
- Cleanup on SSE disconnect

## Flow overview

```
BankTransferAgent turn
  └── ApprovalTool.run(to_user="bob", amount=250.0)
        1. ApprovalService.create(approval_id, user_id, details) → Future
        2. EventForwarder.send_to_user(user_id, {type: "transfer_approval_request", ...})
        3. asyncio.wait_for(asyncio.shield(fut), timeout=30)  ← agent blocks here

              Browser receives WS event, shows approval dialog

              POST /api/banking/approval {approval_id, approved: true}
                └── ApprovalController → ApprovalService.resolve(approval_id, user_id, True)
                      └── fut.set_result(True)    ← agent unblocks

        4. Writes one-shot token → ctx.agent_context.metadata["transfer_approved"]
        5. Returns {"approved": True}

  └── TransferFundsTool.run(to_user, amount)
        Validates + consumes the one-shot token
        Executes transfer in BankDatabase
        Broadcasts balance_changed to all WS connections
```

## ApprovalService

```python
# app/ai/approval/approval_service.py
@injectable(scope=Scope.SINGLETON)
class ApprovalService:
    async def create(
        self,
        approval_id: str,
        user_id: str,
        details: dict,
        conversation_id: str = "",
    ) -> asyncio.Future[bool]:
        """Register a pending approval; return the Future the agent will await."""
        ...

    async def resolve(self, approval_id: str, user_id: str, approved: bool) -> bool:
        """Complete the Future. Returns False if unknown, already consumed, or user_id mismatch."""
        ...

    async def cancel_for_conversation(self, conversation_id: str) -> int:
        """Resolve all pending approvals for a conversation as approved=False. Returns count."""
        ...
```

The `user_id` stored at `create()` time is checked in `resolve()` — a different
authenticated user cannot approve another user's transfer.

## ApprovalTool

```python
# app/ai/approval/approval_tool.py
@tool()
class ApprovalTool:
    def __init__(self, approval_svc: ApprovalService, forwarder: EventForwarder) -> None: ...

    async def run(
        self, ctx: ToolContext, to_user: str, amount: float, description: str = ""
    ) -> dict:
        auth_uid = ctx.execution_context.request.state.get("user_id")
        conv_id = ctx.agent_context.metadata.get("conversation_id", "")
        approval_id = str(uuid4())

        fut = await self._approval_svc.create(
            approval_id, auth_uid,
            {"to_user": to_user, "amount": amount, "description": description},
            conversation_id=conv_id,
        )

        await self._forwarder.send_to_user(auth_uid, {
            "type": "transfer_approval_request",
            "approval_id": approval_id,
            "from_user": auth_uid,
            "to_user": to_user,
            "amount_usd": amount,
            "description": description,
            "created_at": int(time.time() * 1000),
        })

        try:
            approved = await asyncio.wait_for(asyncio.shield(fut), timeout=30)
        except asyncio.TimeoutError:
            return {"approved": False, "reason": "timeout"}

        if approved:
            ctx.agent_context.metadata["transfer_approved"] = {
                "approval_id": approval_id,
                "to_user": to_user,
                "amount": amount,
                "approved_at": time.time(),
            }
            return {"approved": True, "message": "User approved the transfer."}

        return {"approved": False, "reason": "User has declined the transfer"}
```

`asyncio.shield(fut)` prevents the `Future` from being cancelled when `wait_for`
times out — the `Future` remains resolvable so a late browser response still
arrives cleanly (though the tool has already returned `timeout`).

## ApprovalController

```python
# app/ai/approval/approval_controller.py
@use_guards(SignatureGuard)
@controller("/api/banking")
class ApprovalController:
    def __init__(self, approval_svc: ApprovalService) -> None:
        self._approval_svc = approval_svc

    @post("/approval")
    async def resolve(self, body: Json[ApprovalBody], exec_ctx: ExecutionContext) -> dict:
        user_id = exec_ctx.request.state.get("user_id", "")
        ok = await self._approval_svc.resolve(body.approval_id, user_id, body.approved)
        return {"ok": ok}
```

The `user_id` comes from `request.state` (set by `SignatureGuard`), never from the
request body. This closes the cross-user forgery vector at the HTTP layer.

## One-shot transfer token

After `ApprovalTool` returns `{"approved": True}`, it writes a dict into
`ctx.agent_context.metadata["transfer_approved"]`. `TransferFundsTool.run()` must:

1. Check that `metadata["transfer_approved"]` exists
2. Validate `approval_id`, `to_user`, `amount` match the call arguments
3. Check `approved_at` is within the TTL window
4. **Delete** `metadata["transfer_approved"]` before executing the transfer

A second `TransferFundsTool` call without re-running `ApprovalTool` finds the key
missing and returns an error immediately, preventing replay attacks.

## Cleanup on SSE disconnect

The `generate()` async generator in `BankingChatController` wraps the agent loop
in a `try/finally`:

```python
async def generate():
    try:
        # ... agent routing loop ...
        yield ServerSentEvent(event="done", data="")
    except Exception as exc:
        yield ServerSentEvent(event="error", data=str(exc))
    finally:
        await self._approval_svc.cancel_for_conversation(conv_id)
```

`cancel_for_conversation` resolves every matching `Future` as `approved=False` and
removes it from the registry. A browser refresh or tab close can no longer surface
a zombie approval dialog on reconnect.
