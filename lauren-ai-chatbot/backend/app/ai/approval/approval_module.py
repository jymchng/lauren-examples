"""ApprovalModule — wires ApprovalService and ApprovalController."""

from __future__ import annotations

from lauren import module

from app.ai.approval.approval_controller import ApprovalController
from app.ai.approval.approval_service import ApprovalService
from app.crypto.crypto_module import CryptoModule


@module(
    imports=[CryptoModule],
    providers=[ApprovalService],
    controllers=[ApprovalController],
    exports=[ApprovalService],
)
class ApprovalModule:
    """Provides the HITL approval service and its HTTP endpoint."""
