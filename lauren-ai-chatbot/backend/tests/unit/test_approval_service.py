# NOTE: Do NOT add `from __future__ import annotations` to this file.
"""Unit tests for ApprovalService — manages pending HITL transfer approvals."""

from __future__ import annotations

import asyncio

import pytest

from app.ai.approval_service import ApprovalService


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------


class TestApprovalServiceCreate:
    @pytest.mark.asyncio
    async def test_create_returns_future(self):
        svc = ApprovalService()
        fut = await svc.create("appr-1", "alice", {"to_user": "bob", "amount": 100.0})
        assert isinstance(fut, asyncio.Future)
        assert not fut.done()

    @pytest.mark.asyncio
    async def test_create_stores_metadata(self):
        svc = ApprovalService()
        await svc.create("appr-2", "alice", {"to_user": "charlie", "amount": 50.0})
        # resolve with the correct user to confirm metadata was stored
        ok = await svc.resolve("appr-2", "alice", approved=True)
        assert ok is True

    @pytest.mark.asyncio
    async def test_two_pending_approvals_independent(self):
        svc = ApprovalService()
        fut1 = await svc.create("appr-a", "alice", {})
        fut2 = await svc.create("appr-b", "bob", {})
        await svc.resolve("appr-a", "alice", approved=True)
        assert fut1.done()
        assert not fut2.done()


# ---------------------------------------------------------------------------
# resolve()
# ---------------------------------------------------------------------------


class TestApprovalServiceResolve:
    @pytest.mark.asyncio
    async def test_resolve_approved_sets_future_true(self):
        svc = ApprovalService()
        fut = await svc.create("appr-3", "alice", {})
        ok = await svc.resolve("appr-3", "alice", approved=True)
        assert ok is True
        assert fut.result() is True

    @pytest.mark.asyncio
    async def test_resolve_rejected_sets_future_false(self):
        svc = ApprovalService()
        fut = await svc.create("appr-4", "alice", {})
        ok = await svc.resolve("appr-4", "alice", approved=False)
        assert ok is True
        assert fut.result() is False

    @pytest.mark.asyncio
    async def test_resolve_unknown_approval_id_returns_false(self):
        svc = ApprovalService()
        ok = await svc.resolve("nonexistent", "alice", approved=True)
        assert ok is False

    @pytest.mark.asyncio
    async def test_resolve_wrong_user_returns_false(self):
        """Cross-user forgery attempt — approval_id belongs to alice, resolved as bob."""
        svc = ApprovalService()
        await svc.create("appr-5", "alice", {})
        ok = await svc.resolve("appr-5", "bob", approved=True)
        assert ok is False

    @pytest.mark.asyncio
    async def test_resolve_consumes_approval(self):
        """Second resolve on the same approval_id returns False (already consumed)."""
        svc = ApprovalService()
        await svc.create("appr-6", "alice", {})
        await svc.resolve("appr-6", "alice", approved=True)
        ok = await svc.resolve("appr-6", "alice", approved=True)
        assert ok is False

    @pytest.mark.asyncio
    async def test_resolve_does_not_raise_on_already_done_future(self):
        """Concurrent resolves — second one sees fut.done() == True and skips set_result."""
        svc = ApprovalService()
        fut = await svc.create("appr-7", "alice", {})
        # Manually complete the future before resolve() is called
        fut.set_result(True)
        # resolve() should not raise even though the future is already done
        ok = await svc.resolve("appr-7", "alice", approved=False)
        # ok is False because the entry was already removed (or fut was done but entry still present)
        # Either way, no exception should be raised
        assert isinstance(ok, bool)

    @pytest.mark.asyncio
    async def test_resolve_unblocks_awaiter(self):
        """Simulates the agent awaiting the future while the browser resolves it."""
        svc = ApprovalService()
        fut = await svc.create("appr-8", "alice", {})

        results: list[bool] = []

        async def agent_side():
            results.append(await asyncio.shield(fut))

        async def browser_side():
            await asyncio.sleep(0)  # yield to let agent_side start
            await svc.resolve("appr-8", "alice", approved=True)

        await asyncio.gather(agent_side(), browser_side())
        assert results == [True]
