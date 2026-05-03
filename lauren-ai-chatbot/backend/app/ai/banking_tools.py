# NOTE: Do NOT add `from __future__ import annotations` to this file.
# The @tool() decorator uses inspect.signature() at decoration time to build
# the JSON schema, and PEP 563 lazy evaluation breaks that introspection.
"""Banking tools for the SecureBank Transfer Agent.

All tools are class-based so the BankDatabase singleton is injected via DI.

Security model — ToolContext → AgentContext → ExecutionContext
-------------------------------------------------------------
Every privileged tool (``TransferFundsTool``, ``GetTransactionHistoryTool``)
receives a ``ctx: ToolContext`` parameter.  The authenticated user is read
**exclusively** from::

    ctx.execution_context.request.state.get("user_id")

This value was set on ``request.state`` by ``SignatureGuard`` immediately
after it verified the HMAC-SHA256 signature of the HTTP request body.  It
then flows through the lauren framework's trust chain::

    SignatureGuard.can_activate(ExecutionContext)
        └─ request.state.user_id = <HMAC-verified value>
                │
    AgentRunner.run(..., execution_context=ExecutionContext(request=request))
        └─ AgentContext.execution_context  (same ExecutionContext)
                │
    ToolExecutor._execute_single_tool(...)
        └─ ToolContext.execution_context  (forwarded from AgentContext)
                │
    tool.run(ctx: ToolContext, ...)
        └─ ctx.execution_context.request.state.get("user_id")  ← HERE

At no point does the LLM supply or influence the sender identity.  If
``ctx.execution_context.request.state.user_id`` is absent or does not
belong to a valid account the tool returns a security error immediately.

``GetBalanceTool`` is intentionally unauthenticated — balance lookups are
read-only and needed to check a transfer recipient's account.
"""

import logging

from lauren_ai import ToolContext, tool

from app.banking.bank_db import BankDatabase, Transaction


def _auth_uid(ctx: ToolContext) -> str:
    """Extract the guard-verified user_id from the execution context.

    Traverses ``ctx.execution_context.request.state`` — the full lauren
    trust chain.  Returns an empty string when the chain is incomplete so
    callers can treat a falsy result as "unauthenticated".
    """
    exec_ctx = ctx.execution_context
    if exec_ctx is None:
        return ""
    request = getattr(exec_ctx, "request", None)
    if request is None:
        return ""
    state = getattr(request, "state", None)
    if state is None:
        return ""
    return (state.get("user_id") or "").lower()


@tool()
class GetBalanceTool:
    """Get the current account balance and details for any SecureBank customer.

    Use this to look up any user's balance (alice, bob, or charlie).

    Args:
        user_id: The user whose balance to look up. Must be alice, bob, or charlie.
    """

    def __init__(self, db: BankDatabase) -> None:
        self._db = db

    async def run(self, user_id: str) -> dict:
        account = self._db.get_account(user_id.lower())
        if not account:
            return {
                "error": f"Unknown account holder '{user_id}'. "
                "Valid users are: alice, bob, charlie."
            }
        return {
            "user_id": account.user_id,
            "name": account.name,
            "account_id": account.account_id,
            "balance_usd": account.balance,
            "balance_formatted": f"${account.balance:,.2f}",
        }


@tool()
class TransferFundsTool:
    """Execute a verified fund transfer between SecureBank accounts.

    The sender is always the user authenticated in the current session — the
    agent cannot override this.  Only the recipient and amount are LLM-supplied.

    Args:
        to_user: Recipient user ID (alice, bob, or charlie — cannot equal the
                 authenticated sender).
        amount: Amount in USD to transfer (must be positive, max $100,000).
        description: Optional memo or transfer description.
    """

    def __init__(self, db: BankDatabase) -> None:
        self._db = db

    async def run(
        self,
        ctx: ToolContext,
        to_user: str,
        amount: float,
        description: str = "",
    ) -> dict:
        # ── Security: read sender from ctx.execution_context.request.state ───
        # ctx.execution_context is a lauren ExecutionContext whose .request was
        # populated by SignatureGuard from the HMAC-signed payload.  The LLM
        # never touches this value; it supplies only the recipient and amount.
        auth_uid = _auth_uid(ctx)
        if not auth_uid:
            return {
                "error": (
                    "Security error: no authenticated user found in "
                    "ExecutionContext.request.state.  Cannot authorise a transfer."
                )
            }

        from_acct = self._db.get_account(auth_uid)
        if not from_acct:
            return {
                "error": (
                    f"Security violation: session user '{auth_uid}' "
                    "is not a valid SecureBank account holder."
                )
            }

        result = self._db.transfer(
            from_user=auth_uid,
            to_user=to_user.lower(),
            amount=amount,
            description=description,
        )

        if isinstance(result, str):
            return {"error": result}

        assert isinstance(result, Transaction)
        updated = self._db.get_account(auth_uid)
        return {
            "success": True,
            "transaction_id": result.tx_id,
            "from": result.from_name,
            "to": result.to_name,
            "amount_usd": amount,
            "amount_formatted": f"${amount:,.2f}",
            "new_balance_usd": updated.balance if updated else None,
            "new_balance_formatted": f"${updated.balance:,.2f}" if updated else "N/A",
            "timestamp": result.timestamp,
            "description": result.description,
        }


@tool()
class GetTransactionHistoryTool:
    """Retrieve recent transaction history for the authenticated user.

    History is always fetched for the user authenticated in the current
    session — the agent cannot request another user's history.

    Args:
        limit: Maximum number of transactions to return (1–10, default 5).
    """

    def __init__(self, db: BankDatabase) -> None:
        self._db = db

    async def run(self, ctx: ToolContext, limit: int = 5) -> dict:
        # ── Security: same pattern as TransferFundsTool ───────────────────────
        auth_uid = _auth_uid(ctx)
        if not auth_uid:
            return {
                "error": (
                    "Security error: no authenticated user found in "
                    "ExecutionContext.request.state.  Cannot retrieve history."
                )
            }

        account = self._db.get_account(auth_uid)
        if not account:
            return {
                "error": (
                    f"Security violation: session user '{auth_uid}' "
                    "is not a valid account holder."
                )
            }

        clamped = max(1, min(limit, 10))
        transactions = self._db.get_transactions(auth_uid, limit=clamped)

        return {
            "account_holder": account.name,
            "account_id": account.account_id,
            "current_balance": f"${account.balance:,.2f}",
            "transactions": [
                {
                    "tx_id": t.tx_id,
                    "direction": "sent" if t.from_user == auth_uid else "received",
                    "counterparty": t.to_name if t.from_user == auth_uid else t.from_name,
                    "amount": f"${t.amount:,.2f}",
                    "description": t.description,
                    "timestamp": t.timestamp,
                }
                for t in transactions
            ],
            "total_shown": len(transactions),
        }
