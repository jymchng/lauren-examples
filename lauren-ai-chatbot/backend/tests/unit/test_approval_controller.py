
"""Unit tests for ApprovalController — HTTP endpoint for browser Yes/No responses."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("PAYLOAD_SECRET", "test-secret-abc123")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")

from app.ai.approval.approval_controller import ApprovalBody, ApprovalController
from app.ai.approval.approval_service import ApprovalService
from lauren.exceptions import RouteNotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(user_id: str = "alice") -> MagicMock:
    state = MagicMock()
    state.get = lambda k, default=None: user_id if k == "user_id" else default
    req = MagicMock()
    req.state = state
    return req


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestApprovalController:
    @pytest.mark.asyncio
    async def test_valid_approval_returns_ok(self):
        svc = ApprovalService()
        await svc.create("appr-ctrl-1", "alice", {})
        ctrl = ApprovalController(approval_svc=svc)

        body = ApprovalBody(approval_id="appr-ctrl-1", approved=True, user_id="alice")
        result = await ctrl.respond(body=body, request=_make_request("alice"))
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_valid_rejection_returns_ok(self):
        svc = ApprovalService()
        await svc.create("appr-ctrl-2", "alice", {})
        ctrl = ApprovalController(approval_svc=svc)

        body = ApprovalBody(approval_id="appr-ctrl-2", approved=False, user_id="alice")
        result = await ctrl.respond(body=body, request=_make_request("alice"))
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_unknown_approval_id_raises_not_found(self):
        svc = ApprovalService()
        ctrl = ApprovalController(approval_svc=svc)

        body = ApprovalBody(approval_id="nonexistent", approved=True, user_id="alice")
        with pytest.raises(RouteNotFoundError) as exc_info:
            await ctrl.respond(body=body, request=_make_request("alice"))
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_wrong_user_raises_not_found(self):
        """bob tries to resolve alice's approval — must be rejected."""
        svc = ApprovalService()
        await svc.create("appr-ctrl-3", "alice", {})
        ctrl = ApprovalController(approval_svc=svc)

        body = ApprovalBody(approval_id="appr-ctrl-3", approved=True, user_id="bob")
        with pytest.raises(RouteNotFoundError) as exc_info:
            await ctrl.respond(body=body, request=_make_request("bob"))
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_already_consumed_raises_not_found(self):
        """Second resolve on same approval_id returns 404."""
        svc = ApprovalService()
        await svc.create("appr-ctrl-4", "alice", {})
        ctrl = ApprovalController(approval_svc=svc)

        body = ApprovalBody(approval_id="appr-ctrl-4", approved=True, user_id="alice")
        await ctrl.respond(body=body, request=_make_request("alice"))

        with pytest.raises(RouteNotFoundError) as exc_info:
            await ctrl.respond(body=body, request=_make_request("alice"))
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_state_user_id_takes_precedence_over_body(self):
        """request.state.user_id (guard-verified) wins over body.user_id."""
        svc = ApprovalService()
        # Approval belongs to alice
        await svc.create("appr-ctrl-5", "alice", {})
        ctrl = ApprovalController(approval_svc=svc)

        # State says alice; body says bob (should be ignored in favour of state)
        body = ApprovalBody(approval_id="appr-ctrl-5", approved=True, user_id="bob")
        result = await ctrl.respond(body=body, request=_make_request("alice"))
        assert result == {"status": "ok"}
