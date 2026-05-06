# NOTE: Do NOT add `from __future__ import annotations` to this file.
# @tool() uses inspect.signature() at decoration time; PEP 563 breaks it.
"""Unit tests for banking tools: GetBalanceTool, TransferFundsTool, GetTransactionHistoryTool.

Tests are organised around two layers:
- HITL gate (TransferFundsTool): no/invalid approval token → rejects before the DB call
- Security model: no/invalid execution_context → security error
- Happy path: valid token + valid context → performs the operation
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from app.ai.tools.banking_tools import (
    GetBalanceTool,
    GetTransactionHistoryTool,
    TransferFundsTool,
    _auth_uid,
)
from app.banking.bank_db import BankDatabase


# ---------------------------------------------------------------------------
# Helpers — build fake ToolContext with various execution_context states
# ---------------------------------------------------------------------------


def _make_ctx(
    user_id: str | None = None,
    *,
    approval_token: dict | None = None,
) -> MagicMock:
    """Return a ToolContext mock with execution_context.request.state set.

    ``approval_token`` is placed into ``ctx.agent_context.metadata`` so that
    TransferFundsTool's HITL gate can find it.  Pass a dict produced by
    ``_valid_token()`` for happy-path tests, or ``None`` (default) to test
    rejection at the gate.
    """
    ctx = MagicMock()
    if user_id is None:
        ctx.execution_context = None
    else:
        state = MagicMock()
        state.get = lambda k, default=None: user_id if k == "user_id" else default
        request = MagicMock()
        request.state = state
        exec_ctx = MagicMock()
        exec_ctx.request = request
        ctx.execution_context = exec_ctx

    # agent_context.metadata holds the one-shot approval token written by ApprovalTool
    # The token is stored at metadata["transfer_approved"], not spread into metadata.
    agent_ctx = MagicMock()
    agent_ctx.metadata = {"transfer_approved": dict(approval_token)} if approval_token else {}
    ctx.agent_context = agent_ctx

    return ctx


def _make_ctx_no_request(*, approval_token: dict | None = None) -> MagicMock:
    ctx = MagicMock()
    exec_ctx = MagicMock()
    exec_ctx.request = None
    ctx.execution_context = exec_ctx
    agent_ctx = MagicMock()
    agent_ctx.metadata = {"transfer_approved": dict(approval_token)} if approval_token else {}
    ctx.agent_context = agent_ctx
    return ctx


def _make_ctx_no_state(*, approval_token: dict | None = None) -> MagicMock:
    ctx = MagicMock()
    exec_ctx = MagicMock()
    request = MagicMock()
    request.state = None
    exec_ctx.request = request
    ctx.execution_context = exec_ctx
    agent_ctx = MagicMock()
    agent_ctx.metadata = {"transfer_approved": dict(approval_token)} if approval_token else {}
    ctx.agent_context = agent_ctx
    return ctx


def _valid_token(to_user: str = "bob", amount: float = 100.0) -> dict:
    """Return a fresh, non-expired approval token for the given transfer details."""
    return {
        "approved": True,
        "approval_id": "test-approval-id",
        "conversation_id": "test-conv",
        "to_user": to_user,
        "amount": amount,
        "approved_at": time.time(),
    }


@pytest.fixture()
def db() -> BankDatabase:
    return BankDatabase()


# ---------------------------------------------------------------------------
# _auth_uid helper
# ---------------------------------------------------------------------------


class TestAuthUid:
    def test_none_exec_ctx_returns_empty(self):
        ctx = _make_ctx(None)
        assert _auth_uid(ctx) == ""

    def test_no_request_returns_empty(self):
        assert _auth_uid(_make_ctx_no_request()) == ""

    def test_no_state_returns_empty(self):
        assert _auth_uid(_make_ctx_no_state()) == ""

    def test_valid_state_returns_lowercase_uid(self):
        ctx = _make_ctx("Alice")
        assert _auth_uid(ctx) == "alice"

    def test_empty_user_id_returns_empty(self):
        ctx = _make_ctx("")
        assert _auth_uid(ctx) == ""


# ---------------------------------------------------------------------------
# GetBalanceTool
# ---------------------------------------------------------------------------


class TestGetBalanceTool:
    @pytest.mark.asyncio
    async def test_no_exec_ctx_returns_security_error(self, db):
        tool = GetBalanceTool(db=db)
        result = await tool.run(user_id="alice", ctx=_make_ctx(None))
        assert "error" in result
        assert "Security" in result["error"]

    @pytest.mark.asyncio
    async def test_wrong_user_in_ctx_returns_security_error(self, db):
        """ctx says 'bob' but tool is asked for 'alice' — should error."""
        tool = GetBalanceTool(db=db)
        result = await tool.run(user_id="alice", ctx=_make_ctx("bob"))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_account_returns_error(self, db):
        tool = GetBalanceTool(db=db)
        result = await tool.run(user_id="dave", ctx=_make_ctx("dave"))
        assert "error" in result
        assert "dave" in result["error"]

    @pytest.mark.asyncio
    async def test_valid_alice_returns_balance(self, db):
        tool = GetBalanceTool(db=db)
        result = await tool.run(user_id="alice", ctx=_make_ctx("alice"))
        assert "error" not in result
        assert result["user_id"] == "alice"
        assert result["balance_usd"] == 5_000.00
        assert "$5,000.00" in result["balance_formatted"]

    @pytest.mark.asyncio
    async def test_valid_bob_returns_balance(self, db):
        tool = GetBalanceTool(db=db)
        result = await tool.run(user_id="bob", ctx=_make_ctx("bob"))
        assert result["balance_usd"] == 3_200.00

    @pytest.mark.asyncio
    async def test_result_has_account_id(self, db):
        tool = GetBalanceTool(db=db)
        result = await tool.run(user_id="alice", ctx=_make_ctx("alice"))
        assert result["account_id"] == "ACC-001"


# ---------------------------------------------------------------------------
# TransferFundsTool — HITL gate tests
# ---------------------------------------------------------------------------


class TestTransferFundsTool:
    # ── HITL gate: token missing or invalid ──────────────────────────────────

    @pytest.mark.asyncio
    async def test_no_approval_token_returns_approval_required_error(self, db):
        """No token in agent_context.metadata → tool demands approval first."""
        tool = TransferFundsTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), to_user="bob", amount=100.0)
        assert "error" in result
        assert "approval" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_token_with_wrong_to_user_returns_mismatch_error(self, db):
        token = _valid_token(to_user="charlie", amount=100.0)
        tool = TransferFundsTool(db=db)
        result = await tool.run(
            ctx=_make_ctx("alice", approval_token=token),
            to_user="bob",
            amount=100.0,
        )
        assert "error" in result
        assert "do not match" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_token_with_wrong_amount_returns_mismatch_error(self, db):
        token = _valid_token(to_user="bob", amount=50.0)
        tool = TransferFundsTool(db=db)
        result = await tool.run(
            ctx=_make_ctx("alice", approval_token=token),
            to_user="bob",
            amount=100.0,
        )
        assert "error" in result
        assert "amount" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_expired_token_returns_expiry_error(self, db):
        token = _valid_token(to_user="bob", amount=100.0)
        token["approved_at"] = time.time() - 120  # 120 s ago > 60 s limit
        tool = TransferFundsTool(db=db)
        result = await tool.run(
            ctx=_make_ctx("alice", approval_token=token),
            to_user="bob",
            amount=100.0,
        )
        assert "error" in result
        assert "expired" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_token_consumed_after_use(self, db):
        """Approval token is deleted from metadata after a successful transfer."""
        token = _valid_token(to_user="bob", amount=100.0)
        ctx = _make_ctx("alice", approval_token=token)
        tool = TransferFundsTool(db=db)
        await tool.run(ctx=ctx, to_user="bob", amount=100.0)
        assert "transfer_approved" not in ctx.agent_context.metadata

    @pytest.mark.asyncio
    async def test_amount_within_tolerance_passes(self, db):
        """Floating-point amounts within 0.001 tolerance should not be rejected."""
        token = _valid_token(to_user="bob", amount=100.000_0001)
        tool = TransferFundsTool(db=db)
        result = await tool.run(
            ctx=_make_ctx("alice", approval_token=token),
            to_user="bob",
            amount=100.0,
        )
        assert result.get("success") is True

    # ── Security layer (reached only after a valid approval token) ───────────

    @pytest.mark.asyncio
    async def test_no_exec_ctx_returns_security_error(self, db):
        """Token passes but exec_ctx is None → security error."""
        tool = TransferFundsTool(db=db)
        token = _valid_token(to_user="bob", amount=100.0)
        result = await tool.run(
            ctx=_make_ctx(None, approval_token=token),
            to_user="bob",
            amount=100.0,
        )
        assert "error" in result
        assert "Security" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_session_user_returns_security_error(self, db):
        """User 'dave' is not in the bank — should be rejected as a security violation."""
        tool = TransferFundsTool(db=db)
        token = _valid_token(to_user="bob", amount=100.0)
        result = await tool.run(
            ctx=_make_ctx("dave", approval_token=token),
            to_user="bob",
            amount=100.0,
        )
        assert "error" in result
        assert "Security" in result["error"] or "violation" in result["error"].lower()

    # ── Happy path ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_successful_transfer(self, db):
        tool = TransferFundsTool(db=db)
        token = _valid_token(to_user="bob", amount=500.0)
        result = await tool.run(
            ctx=_make_ctx("alice", approval_token=token),
            to_user="bob",
            amount=500.0,
        )
        assert result.get("success") is True
        assert result["amount_usd"] == 500.0
        assert "transaction_id" in result
        assert result["transaction_id"].startswith("TXN-")

    @pytest.mark.asyncio
    async def test_successful_transfer_updates_balance(self, db):
        tool = TransferFundsTool(db=db)
        token = _valid_token(to_user="bob", amount=200.0)
        await tool.run(ctx=_make_ctx("alice", approval_token=token), to_user="bob", amount=200.0)
        alice = db.get_account("alice")
        assert alice.balance == 4_800.00

    @pytest.mark.asyncio
    async def test_transfer_error_returns_error_dict(self, db):
        """Insufficient funds → db.transfer returns a string → tool wraps in {"error": ...}."""
        tool = TransferFundsTool(db=db)
        token = _valid_token(to_user="alice", amount=999_999.0)
        result = await tool.run(
            ctx=_make_ctx("charlie", approval_token=token),
            to_user="alice",
            amount=999_999.0,
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_transfer_with_description(self, db):
        tool = TransferFundsTool(db=db)
        token = _valid_token(to_user="bob", amount=50.0)
        result = await tool.run(
            ctx=_make_ctx("alice", approval_token=token),
            to_user="bob",
            amount=50.0,
            description="rent",
        )
        assert result.get("success") is True
        assert result["description"] == "rent"

    @pytest.mark.asyncio
    async def test_result_has_formatted_amounts(self, db):
        tool = TransferFundsTool(db=db)
        token = _valid_token(to_user="bob", amount=1_234.56)
        result = await tool.run(
            ctx=_make_ctx("alice", approval_token=token),
            to_user="bob",
            amount=1_234.56,
        )
        assert "$1,234.56" in result["amount_formatted"]
        assert result["new_balance_usd"] is not None


# ---------------------------------------------------------------------------
# GetTransactionHistoryTool
# ---------------------------------------------------------------------------


class TestGetTransactionHistoryTool:
    @pytest.mark.asyncio
    async def test_no_exec_ctx_returns_security_error(self, db):
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx(None), user_id="alice")
        assert "error" in result
        assert "Security" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_session_user_returns_security_error(self, db):
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("dave"), user_id="dave")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_user_id_mismatch_returns_security_error(self, db):
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), user_id="bob")
        assert "error" in result
        assert "Security violation" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_history(self, db):
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), user_id="alice")
        assert "error" not in result
        assert result["total_shown"] == 0
        assert result["transactions"] == []

    @pytest.mark.asyncio
    async def test_history_after_transfers(self, db):
        db.transfer("alice", "bob", 100.0, "t1")
        db.transfer("bob", "alice", 50.0, "t2")
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), user_id="alice")
        assert result["total_shown"] == 2

    @pytest.mark.asyncio
    async def test_limit_clamped_to_10(self, db):
        for i in range(15):
            db.transfer("alice", "bob", 1.0, f"t{i}")
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), user_id="alice", limit=20)
        assert result["total_shown"] <= 10

    @pytest.mark.asyncio
    async def test_limit_clamped_to_1(self, db):
        db.transfer("alice", "bob", 10.0, "only")
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), user_id="alice", limit=0)
        assert result["total_shown"] == 1

    @pytest.mark.asyncio
    async def test_transaction_direction_sent(self, db):
        db.transfer("alice", "bob", 100.0, "to bob")
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), user_id="alice")
        txn = result["transactions"][0]
        assert txn["direction"] == "sent"

    @pytest.mark.asyncio
    async def test_transaction_direction_received(self, db):
        db.transfer("bob", "alice", 100.0, "from bob")
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), user_id="alice")
        txn = result["transactions"][0]
        assert txn["direction"] == "received"

    @pytest.mark.asyncio
    async def test_result_has_account_metadata(self, db):
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), user_id="alice")
        assert result["account_holder"] == "Alice Johnson"
        assert result["account_id"] == "ACC-001"
        assert "$5,000.00" in result["current_balance"]
