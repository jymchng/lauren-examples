# NOTE: Do NOT add `from __future__ import annotations` to this file.
"""Unit tests for ApprovalTool — HITL gate that blocks until user approves/declines."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.approval.approval_service import ApprovalService
from app.ai.approval.approval_tool import ApprovalTool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool_ctx(user_id: str | None = "alice", conversation_id: str = "conv-1") -> MagicMock:
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

    agent_ctx = MagicMock()
    agent_ctx.metadata = {"conversation_id": conversation_id}
    ctx.agent_context = agent_ctx
    return ctx


def _make_forwarder() -> MagicMock:
    fwd = MagicMock()
    fwd.send_to_user = AsyncMock()
    return fwd


# ---------------------------------------------------------------------------
# No authenticated user
# ---------------------------------------------------------------------------


class TestApprovalToolNoAuth:
    @pytest.mark.asyncio
    async def test_no_exec_ctx_returns_error(self):
        svc = ApprovalService()
        fwd = _make_forwarder()
        tool = ApprovalTool(approval_svc=svc, forwarder=fwd)
        result = await tool.run(_make_tool_ctx(None), to_user="bob", amount=100.0)
        assert "error" in result
        assert "Security" in result["error"]

    @pytest.mark.asyncio
    async def test_no_auth_does_not_send_ws_event(self):
        svc = ApprovalService()
        fwd = _make_forwarder()
        tool = ApprovalTool(approval_svc=svc, forwarder=fwd)
        await tool.run(_make_tool_ctx(None), to_user="bob", amount=100.0)
        fwd.send_to_user.assert_not_called()


# ---------------------------------------------------------------------------
# Approval flow — approved
# ---------------------------------------------------------------------------


class TestApprovalToolApproved:
    @pytest.mark.asyncio
    async def test_approved_returns_approved_true(self):
        svc = ApprovalService()
        fwd = _make_forwarder()
        tool = ApprovalTool(approval_svc=svc, forwarder=fwd)
        ctx = _make_tool_ctx("alice")

        async def _approve():
            # Wait for the approval to be registered, then resolve it
            await asyncio.sleep(0)
            async with svc._lock:
                approval_id = next(iter(svc._pending))
            await svc.resolve(approval_id, "alice", approved=True)

        result, _ = await asyncio.gather(
            tool.run(ctx, to_user="bob", amount=100.0),
            _approve(),
        )
        assert result["approved"] is True
        assert "message" in result

    @pytest.mark.asyncio
    async def test_approved_writes_token_to_metadata(self):
        svc = ApprovalService()
        fwd = _make_forwarder()
        tool = ApprovalTool(approval_svc=svc, forwarder=fwd)
        ctx = _make_tool_ctx("alice")

        async def _approve():
            await asyncio.sleep(0)
            async with svc._lock:
                approval_id = next(iter(svc._pending))
            await svc.resolve(approval_id, "alice", approved=True)

        await asyncio.gather(tool.run(ctx, to_user="bob", amount=100.0), _approve())

        token = ctx.agent_context.metadata.get("transfer_approved")
        assert token is not None
        assert token["approved"] is True
        assert token["to_user"] == "bob"
        assert token["amount"] == 100.0

    @pytest.mark.asyncio
    async def test_approved_sends_ws_event(self):
        svc = ApprovalService()
        fwd = _make_forwarder()
        tool = ApprovalTool(approval_svc=svc, forwarder=fwd)
        ctx = _make_tool_ctx("alice")

        async def _approve():
            await asyncio.sleep(0)
            async with svc._lock:
                approval_id = next(iter(svc._pending))
            await svc.resolve(approval_id, "alice", approved=True)

        await asyncio.gather(tool.run(ctx, to_user="bob", amount=100.0), _approve())

        fwd.send_to_user.assert_called_once()
        call_args = fwd.send_to_user.call_args
        payload = call_args[0][1]
        assert payload["type"] == "transfer_approval_request"
        assert payload["to_user"] == "bob"
        assert payload["amount_usd"] == 100.0
        assert payload["from_user"] == "alice"

    @pytest.mark.asyncio
    async def test_approved_token_has_approved_at_timestamp(self):
        svc = ApprovalService()
        fwd = _make_forwarder()
        tool = ApprovalTool(approval_svc=svc, forwarder=fwd)
        ctx = _make_tool_ctx("alice")
        before = time.time()

        async def _approve():
            await asyncio.sleep(0)
            async with svc._lock:
                approval_id = next(iter(svc._pending))
            await svc.resolve(approval_id, "alice", approved=True)

        await asyncio.gather(tool.run(ctx, to_user="bob", amount=50.0), _approve())
        after = time.time()

        token = ctx.agent_context.metadata["transfer_approved"]
        assert before <= token["approved_at"] <= after


# ---------------------------------------------------------------------------
# Approval flow — declined
# ---------------------------------------------------------------------------


class TestApprovalToolDeclined:
    @pytest.mark.asyncio
    async def test_declined_returns_approved_false(self):
        svc = ApprovalService()
        fwd = _make_forwarder()
        tool = ApprovalTool(approval_svc=svc, forwarder=fwd)
        ctx = _make_tool_ctx("alice")

        async def _decline():
            await asyncio.sleep(0)
            async with svc._lock:
                approval_id = next(iter(svc._pending))
            await svc.resolve(approval_id, "alice", approved=False)

        result, _ = await asyncio.gather(
            tool.run(ctx, to_user="bob", amount=100.0),
            _decline(),
        )
        assert result["approved"] is False
        assert result.get("reason") == "User has declined the transfer"

    @pytest.mark.asyncio
    async def test_declined_does_not_write_token_to_metadata(self):
        svc = ApprovalService()
        fwd = _make_forwarder()
        tool = ApprovalTool(approval_svc=svc, forwarder=fwd)
        ctx = _make_tool_ctx("alice")

        async def _decline():
            await asyncio.sleep(0)
            async with svc._lock:
                approval_id = next(iter(svc._pending))
            await svc.resolve(approval_id, "alice", approved=False)

        await asyncio.gather(tool.run(ctx, to_user="bob", amount=100.0), _decline())
        assert "transfer_approved" not in ctx.agent_context.metadata


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestApprovalToolTimeout:
    @pytest.mark.asyncio
    async def test_timeout_returns_approval_timeout(self, monkeypatch):
        """Patch asyncio.wait_for to raise TimeoutError immediately."""
        import app.ai.approval.approval_tool as _mod

        async def _fake_wait_for(coro, timeout):
            raise asyncio.TimeoutError

        monkeypatch.setattr(_mod.asyncio, "wait_for", _fake_wait_for)

        svc = ApprovalService()
        fwd = _make_forwarder()
        tool = ApprovalTool(approval_svc=svc, forwarder=fwd)
        result = await tool.run(_make_tool_ctx("alice"), to_user="bob", amount=100.0)
        assert result["approved"] is False
        assert "30" in result["reason"] or "timeout" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_timeout_does_not_write_token(self, monkeypatch):
        import app.ai.approval.approval_tool as _mod

        async def _fake_wait_for(coro, timeout):
            raise asyncio.TimeoutError

        monkeypatch.setattr(_mod.asyncio, "wait_for", _fake_wait_for)

        svc = ApprovalService()
        fwd = _make_forwarder()
        tool = ApprovalTool(approval_svc=svc, forwarder=fwd)
        ctx = _make_tool_ctx("alice")
        await tool.run(ctx, to_user="bob", amount=100.0)
        assert "transfer_approved" not in ctx.agent_context.metadata
