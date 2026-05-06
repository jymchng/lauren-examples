"""ApprovalController — receives the browser's Yes/No response for a pending transfer.

The controller is protected by ``SignatureGuard`` so that only requests signed
by the Next.js proxy (holding the HMAC secret) can resolve approvals.  This
prevents a malicious browser from forging an approval for another user's request.

``ApprovalService.resolve()`` additionally checks that the ``user_id`` in the
body matches the one stored when the approval was created, providing a second
line of defence against cross-user forgery.
"""

from __future__ import annotations

from pydantic import BaseModel

from lauren import Json, Request, controller, post, use_guards
from lauren.exceptions import RouteNotFoundError

from app.ai.approval.approval_service import ApprovalService
from app.crypto.signature_guard import SignatureGuard


class ApprovalBody(BaseModel):
    """Request body for POST /api/banking/approval."""

    approval_id: str
    approved: bool
    user_id: str


@use_guards(SignatureGuard)
@controller("/api/banking")
class ApprovalController:
    """Resolves a pending human-in-the-loop transfer approval."""

    def __init__(self, approval_svc: ApprovalService) -> None:
        self._approval_svc = approval_svc

    @post("/approval")
    async def respond(
        self,
        body: Json[ApprovalBody],
        request: Request,
    ) -> dict:
        """Accept or reject a pending transfer approval.

        The ``user_id`` is read from both the request state (pinned by
        ``SignatureGuard``) and the body.  The service performs its own
        cross-user check as a second layer of defence.
        """
        user_id = (request.state.get("user_id") or body.user_id).lower()
        ok = await self._approval_svc.resolve(
            body.approval_id,
            user_id,
            body.approved,
        )
        if not ok:
            raise RouteNotFoundError("Approval request not found or already consumed")
        return {"status": "ok"}
