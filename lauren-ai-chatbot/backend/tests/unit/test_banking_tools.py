# NOTE: Do NOT add `from __future__ import annotations` to this file.
# @tool() uses inspect.signature() at decoration time; PEP 563 breaks it.
"""Unit tests for banking tools: GetBalanceTool, TransferFundsTool, GetTransactionHistoryTool.

Tests are organised around the security model:
- No execution_context → returns security error
- Invalid account in context → returns security error
- Valid context → performs the operation
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.ai.banking_tools import (
    GetBalanceTool,
    GetTransactionHistoryTool,
    TransferFundsTool,
    _auth_uid,
)
from app.banking.bank_db import BankDatabase


# ---------------------------------------------------------------------------
# Helpers — build fake ToolContext with various execution_context states
# ---------------------------------------------------------------------------


def _make_ctx(user_id: str | None = None) -> MagicMock:
    """Return a ToolContext mock with execution_context.request.state set."""
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
    return ctx


def _make_ctx_no_request() -> MagicMock:
    ctx = MagicMock()
    exec_ctx = MagicMock()
    exec_ctx.request = None
    ctx.execution_context = exec_ctx
    return ctx


def _make_ctx_no_state() -> MagicMock:
    ctx = MagicMock()
    exec_ctx = MagicMock()
    request = MagicMock()
    request.state = None
    exec_ctx.request = request
    ctx.execution_context = exec_ctx
    return ctx


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
# TransferFundsTool
# ---------------------------------------------------------------------------


class TestTransferFundsTool:
    @pytest.mark.asyncio
    async def test_no_exec_ctx_returns_security_error(self, db):
        tool = TransferFundsTool(db=db)
        result = await tool.run(ctx=_make_ctx(None), to_user="bob", amount=100.0)
        assert "error" in result
        assert "Security" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_session_user_returns_security_error(self, db):
        """User 'dave' is not in the bank — should be rejected as a security violation."""
        tool = TransferFundsTool(db=db)
        result = await tool.run(ctx=_make_ctx("dave"), to_user="bob", amount=100.0)
        assert "error" in result
        assert "Security" in result["error"] or "violation" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_successful_transfer(self, db):
        tool = TransferFundsTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), to_user="bob", amount=500.0)
        assert result.get("success") is True
        assert result["amount_usd"] == 500.0
        assert "transaction_id" in result
        assert result["transaction_id"].startswith("TXN-")

    @pytest.mark.asyncio
    async def test_successful_transfer_updates_balance(self, db):
        tool = TransferFundsTool(db=db)
        await tool.run(ctx=_make_ctx("alice"), to_user="bob", amount=200.0)
        alice = db.get_account("alice")
        assert alice.balance == 4_800.00

    @pytest.mark.asyncio
    async def test_transfer_error_returns_error_dict(self, db):
        """Insufficient funds → db.transfer returns a string → tool wraps in {"error": ...}."""
        tool = TransferFundsTool(db=db)
        result = await tool.run(ctx=_make_ctx("charlie"), to_user="alice", amount=999_999.0)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_transfer_with_description(self, db):
        tool = TransferFundsTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), to_user="bob", amount=50.0, description="rent")
        assert result.get("success") is True
        assert result["description"] == "rent"

    @pytest.mark.asyncio
    async def test_result_has_formatted_amounts(self, db):
        tool = TransferFundsTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), to_user="bob", amount=1_234.56)
        assert "$1,234.56" in result["amount_formatted"]
        assert result["new_balance_usd"] is not None


# ---------------------------------------------------------------------------
# GetTransactionHistoryTool
# ---------------------------------------------------------------------------


class TestGetTransactionHistoryTool:
    @pytest.mark.asyncio
    async def test_no_exec_ctx_returns_security_error(self, db):
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx(None))
        assert "error" in result
        assert "Security" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_session_user_returns_security_error(self, db):
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("dave"))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_empty_history(self, db):
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"))
        assert "error" not in result
        assert result["total_shown"] == 0
        assert result["transactions"] == []

    @pytest.mark.asyncio
    async def test_history_after_transfers(self, db):
        db.transfer("alice", "bob", 100.0, "t1")
        db.transfer("bob", "alice", 50.0, "t2")
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"))
        assert result["total_shown"] == 2

    @pytest.mark.asyncio
    async def test_limit_clamped_to_10(self, db):
        for i in range(15):
            db.transfer("alice", "bob", 1.0, f"t{i}")
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), limit=20)
        assert result["total_shown"] <= 10

    @pytest.mark.asyncio
    async def test_limit_clamped_to_1(self, db):
        db.transfer("alice", "bob", 10.0, "only")
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"), limit=0)
        assert result["total_shown"] == 1

    @pytest.mark.asyncio
    async def test_transaction_direction_sent(self, db):
        db.transfer("alice", "bob", 100.0, "to bob")
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"))
        txn = result["transactions"][0]
        assert txn["direction"] == "sent"

    @pytest.mark.asyncio
    async def test_transaction_direction_received(self, db):
        db.transfer("bob", "alice", 100.0, "from bob")
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"))
        txn = result["transactions"][0]
        assert txn["direction"] == "received"

    @pytest.mark.asyncio
    async def test_result_has_account_metadata(self, db):
        tool = GetTransactionHistoryTool(db=db)
        result = await tool.run(ctx=_make_ctx("alice"))
        assert result["account_holder"] == "Alice Johnson"
        assert result["account_id"] == "ACC-001"
        assert "$5,000.00" in result["current_balance"]
