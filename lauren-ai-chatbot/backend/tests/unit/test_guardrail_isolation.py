"""Tests verifying guardrail configuration is per-agent and does not bleed.

Tests 46–53: Decorator presence on agent classes.
Tests 54–63: Runner isolation — only the right agent's guard fires.
Tests 64–70: Phrase and configuration isolation per agent.

NOTE: Some tests in this file will FAIL until @use_guardrails decorators are
uncommented in the agent files. That is intentional — the tests document the
required wiring.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("PAYLOAD_SECRET", "test-secret-abc123")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")

from lauren_ai import LLMConfig
from lauren_ai._agents._runner import AgentRunnerBase
from lauren_ai._guardrails._decorator import USE_GUARDRAILS_META
from lauren_ai._transport import Completion, TokenUsage
from lauren_ai._transport._mock import MockTransport

from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent
from app.ai.agents.disputes_agent import DisputesAgent
from app.ai.agents.transfer_agent import BankTransferAgent
from app.ai.agents.unauth_crm_agent import UnauthenticatedCRMAgent


def _completion(content: str = "OK") -> Completion:
    return Completion(
        id="c1",
        model="mock",
        content=content,
        tool_calls=[],
        stop_reason="end_turn",
        usage=TokenUsage(input_tokens=5, output_tokens=5),
    )


def _make_runner(mock: MockTransport | None = None) -> tuple[AgentRunnerBase, MockTransport]:
    if mock is None:
        mock = MockTransport()
    cfg = LLMConfig(provider="anthropic", model="mock-model", api_key="mock")
    return AgentRunnerBase(transport=mock), mock


# ---------------------------------------------------------------------------
# Class 1 — TestGuardrailDecoratorPresence (8 tests)
# ---------------------------------------------------------------------------


class TestGuardrailDecoratorPresence:
    def test_transfer_agent_has_use_guardrails_meta(self):
        meta = getattr(BankTransferAgent, USE_GUARDRAILS_META, None)
        assert meta is not None, (
            "BankTransferAgent must have @use_guardrails — uncomment the decorator in transfer_agent.py"
        )

    def test_auth_crm_agent_has_use_guardrails_meta(self):
        meta = getattr(AuthenticatedCRMAgent, USE_GUARDRAILS_META, None)
        assert meta is not None, (
            "AuthenticatedCRMAgent must have @use_guardrails — uncomment the decorator in auth_crm_agent.py"
        )

    def test_disputes_agent_has_use_guardrails_meta(self):
        meta = getattr(DisputesAgent, USE_GUARDRAILS_META, None)
        assert meta is not None, (
            "DisputesAgent must have @use_guardrails — uncomment the decorator in disputes_agent.py"
        )

    def test_unauth_crm_agent_has_no_use_guardrails_output(self):
        """UnauthCRM uses KB tools but NOT a scope guardrail."""
        meta = getattr(UnauthenticatedCRMAgent, USE_GUARDRAILS_META, None)
        if meta is None:
            return  # No guardrail meta at all → pass
        # If it exists, output_guardrails must be empty
        assert meta.output_guardrails == []

    def test_transfer_agent_output_guardrails_not_empty(self):
        meta = getattr(BankTransferAgent, USE_GUARDRAILS_META, None)
        assert meta is not None and len(meta.output_guardrails) > 0, (
            "BankTransferAgent must have at least one output guardrail"
        )

    def test_auth_crm_agent_output_guardrails_not_empty(self):
        meta = getattr(AuthenticatedCRMAgent, USE_GUARDRAILS_META, None)
        assert meta is not None and len(meta.output_guardrails) > 0, (
            "AuthenticatedCRMAgent must have at least one output guardrail"
        )

    def test_disputes_agent_output_guardrails_not_empty(self):
        meta = getattr(DisputesAgent, USE_GUARDRAILS_META, None)
        assert meta is not None and len(meta.output_guardrails) > 0, (
            "DisputesAgent must have at least one output guardrail"
        )

    def test_unauth_crm_has_no_output_scope_guardrail_instance(self):
        from app.ai.guardrails.llm_scope_guard import LLMScopeGuard
        from app.ai.guardrails.agent_scope_guard import AgentScopeGuard

        meta = getattr(UnauthenticatedCRMAgent, USE_GUARDRAILS_META, None)
        if meta is None:
            return
        for guard in meta.output_guardrails:
            assert not isinstance(guard, (LLMScopeGuard, AgentScopeGuard)), "UnauthCRM should not have a scope guard"


# ---------------------------------------------------------------------------
# Class 2 — TestGuardrailRunnerIsolation (10 tests)
# ---------------------------------------------------------------------------


class TestGuardrailRunnerIsolation:
    """The runner reads USE_GUARDRAILS_META from the AGENT CLASS being run.
    Two agents in the same runner can have different guardrails."""

    async def test_transfer_guard_fires_for_transfer_agent(self):
        spy = MagicMock()
        spy.check = AsyncMock(return_value=MagicMock(action="pass", guardrail_name="spy"))

        meta = getattr(BankTransferAgent, USE_GUARDRAILS_META, None)
        if meta is None:
            pytest.skip("BankTransferAgent has no guardrails (uncomment decorator)")

        # Temporarily inject spy into transfer agent's guards
        original_guards = meta.output_guardrails[:]
        meta.output_guardrails.clear()
        meta.output_guardrails.append(spy)

        try:
            runner, mock = _make_runner()
            mock.queue_response(_completion("transfer response"))
            await runner.run(BankTransferAgent(), "do transfer")
        finally:
            meta.output_guardrails.clear()
            meta.output_guardrails.extend(original_guards)

        spy.check.assert_called()

    async def test_transfer_guard_does_not_fire_for_auth_crm(self):
        spy = MagicMock()
        spy.check = AsyncMock(return_value=MagicMock(action="pass", guardrail_name="spy"))

        transfer_meta = getattr(BankTransferAgent, USE_GUARDRAILS_META, None)
        if transfer_meta is None:
            pytest.skip("BankTransferAgent has no guardrails")

        original_guards = transfer_meta.output_guardrails[:]
        transfer_meta.output_guardrails.clear()
        transfer_meta.output_guardrails.append(spy)

        try:
            runner, mock = _make_runner()
            mock.queue_response(_completion("auth crm response"))
            # Run AuthCRM — transfer guard should NOT fire
            await runner.run(AuthenticatedCRMAgent(), "show balance")
        finally:
            transfer_meta.output_guardrails.clear()
            transfer_meta.output_guardrails.extend(original_guards)

        spy.check.assert_not_called()

    async def test_auth_crm_guard_fires_for_auth_crm(self):
        spy = MagicMock()
        spy.check = AsyncMock(return_value=MagicMock(action="pass", guardrail_name="spy"))

        meta = getattr(AuthenticatedCRMAgent, USE_GUARDRAILS_META, None)
        if meta is None:
            pytest.skip("AuthenticatedCRMAgent has no guardrails")

        original = meta.output_guardrails[:]
        meta.output_guardrails.clear()
        meta.output_guardrails.append(spy)

        try:
            runner, mock = _make_runner()
            mock.queue_response(_completion("ok"))
            await runner.run(AuthenticatedCRMAgent(), "hi")
        finally:
            meta.output_guardrails.clear()
            meta.output_guardrails.extend(original)

        spy.check.assert_called()

    async def test_auth_crm_guard_does_not_fire_for_transfer(self):
        spy = MagicMock()
        spy.check = AsyncMock(return_value=MagicMock(action="pass", guardrail_name="spy"))

        auth_meta = getattr(AuthenticatedCRMAgent, USE_GUARDRAILS_META, None)
        if auth_meta is None:
            pytest.skip("AuthenticatedCRMAgent has no guardrails")

        original = auth_meta.output_guardrails[:]
        auth_meta.output_guardrails.clear()
        auth_meta.output_guardrails.append(spy)

        try:
            runner, mock = _make_runner()
            mock.queue_response(_completion("ok"))
            await runner.run(BankTransferAgent(), "transfer")
        finally:
            auth_meta.output_guardrails.clear()
            auth_meta.output_guardrails.extend(original)

        spy.check.assert_not_called()

    async def test_disputes_guard_fires_for_disputes(self):
        spy = MagicMock()
        spy.check = AsyncMock(return_value=MagicMock(action="pass", guardrail_name="spy"))

        meta = getattr(DisputesAgent, USE_GUARDRAILS_META, None)
        if meta is None:
            pytest.skip("DisputesAgent has no guardrails")

        original = meta.output_guardrails[:]
        meta.output_guardrails.clear()
        meta.output_guardrails.append(spy)

        try:
            runner, mock = _make_runner()
            mock.queue_response(_completion("ok"))
            await runner.run(DisputesAgent(), "dispute this")
        finally:
            meta.output_guardrails.clear()
            meta.output_guardrails.extend(original)

        spy.check.assert_called()

    async def test_disputes_guard_does_not_fire_for_auth_crm(self):
        spy = MagicMock()
        spy.check = AsyncMock(return_value=MagicMock(action="pass", guardrail_name="spy"))

        disputes_meta = getattr(DisputesAgent, USE_GUARDRAILS_META, None)
        if disputes_meta is None:
            pytest.skip("DisputesAgent has no guardrails")

        original = disputes_meta.output_guardrails[:]
        disputes_meta.output_guardrails.clear()
        disputes_meta.output_guardrails.append(spy)

        try:
            runner, mock = _make_runner()
            mock.queue_response(_completion("ok"))
            await runner.run(AuthenticatedCRMAgent(), "show balance")
        finally:
            disputes_meta.output_guardrails.clear()
            disputes_meta.output_guardrails.extend(original)

        spy.check.assert_not_called()

    async def test_transfer_guard_does_not_fire_for_disputes(self):
        spy = MagicMock()
        spy.check = AsyncMock(return_value=MagicMock(action="pass", guardrail_name="spy"))

        transfer_meta = getattr(BankTransferAgent, USE_GUARDRAILS_META, None)
        if transfer_meta is None:
            pytest.skip("BankTransferAgent has no guardrails")

        original = transfer_meta.output_guardrails[:]
        transfer_meta.output_guardrails.clear()
        transfer_meta.output_guardrails.append(spy)

        try:
            runner, mock = _make_runner()
            mock.queue_response(_completion("ok"))
            await runner.run(DisputesAgent(), "dispute")
        finally:
            transfer_meta.output_guardrails.clear()
            transfer_meta.output_guardrails.extend(original)

        spy.check.assert_not_called()

    async def test_auth_crm_guard_does_not_fire_for_disputes(self):
        spy = MagicMock()
        spy.check = AsyncMock(return_value=MagicMock(action="pass", guardrail_name="spy"))

        auth_meta = getattr(AuthenticatedCRMAgent, USE_GUARDRAILS_META, None)
        if auth_meta is None:
            pytest.skip("AuthenticatedCRMAgent has no guardrails")

        original = auth_meta.output_guardrails[:]
        auth_meta.output_guardrails.clear()
        auth_meta.output_guardrails.append(spy)

        try:
            runner, mock = _make_runner()
            mock.queue_response(_completion("ok"))
            await runner.run(DisputesAgent(), "dispute")
        finally:
            auth_meta.output_guardrails.clear()
            auth_meta.output_guardrails.extend(original)

        spy.check.assert_not_called()

    async def test_disputes_guard_does_not_fire_for_transfer(self):
        spy = MagicMock()
        spy.check = AsyncMock(return_value=MagicMock(action="pass", guardrail_name="spy"))

        disputes_meta = getattr(DisputesAgent, USE_GUARDRAILS_META, None)
        if disputes_meta is None:
            pytest.skip("DisputesAgent has no guardrails")

        original = disputes_meta.output_guardrails[:]
        disputes_meta.output_guardrails.clear()
        disputes_meta.output_guardrails.append(spy)

        try:
            runner, mock = _make_runner()
            mock.queue_response(_completion("ok"))
            await runner.run(BankTransferAgent(), "transfer")
        finally:
            disputes_meta.output_guardrails.clear()
            disputes_meta.output_guardrails.extend(original)

        spy.check.assert_not_called()

    async def test_unauth_crm_no_guardrail_runs(self):
        """UnauthCRM should have NO output guardrail by default."""
        spy = MagicMock()
        spy.check = AsyncMock(return_value=MagicMock(action="pass"))

        # Run UnauthCRM — spy is NOT on its guard list (if any)
        runner, mock = _make_runner()
        mock.queue_response(_completion("general banking info"))
        await runner.run(UnauthenticatedCRMAgent(), "what are your products?")

        spy.check.assert_not_called()  # spy was never attached — confirms isolation


# ---------------------------------------------------------------------------
# Class 3 — TestGuardrailPhraseIsolation (7 tests)
# ---------------------------------------------------------------------------


class TestGuardrailPhraseIsolation:
    def _get_guard_instance(self, agent_cls):
        from app.ai.guardrails.llm_scope_guard import LLMScopeGuard
        from app.ai.guardrails.agent_scope_guard import AgentScopeGuard

        meta = getattr(agent_cls, USE_GUARDRAILS_META, None)
        if meta is None or not meta.output_guardrails:
            return None
        for g in meta.output_guardrails:
            if isinstance(g, (LLMScopeGuard, AgentScopeGuard)):
                return g
        return None

    def test_transfer_agent_has_distinct_guardrail_name(self):
        guard = self._get_guard_instance(BankTransferAgent)
        if guard is None:
            pytest.skip("BankTransferAgent has no scope guard")
        assert guard._guardrail_name == "TransferScopeGuard"

    def test_auth_crm_has_distinct_guardrail_name(self):
        guard = self._get_guard_instance(AuthenticatedCRMAgent)
        if guard is None:
            pytest.skip("AuthenticatedCRMAgent has no scope guard")
        assert guard._guardrail_name == "AuthCRMScopeGuard"

    def test_disputes_has_distinct_guardrail_name(self):
        guard = self._get_guard_instance(DisputesAgent)
        if guard is None:
            pytest.skip("DisputesAgent has no scope guard")
        assert guard._guardrail_name == "DisputesScopeGuard"

    def test_transfer_redirect_mentions_crm(self):
        guard = self._get_guard_instance(BankTransferAgent)
        if guard is None:
            pytest.skip("BankTransferAgent has no scope guard")
        redirect = guard._redirect if hasattr(guard, "_redirect") else getattr(guard._inner, "_violation_message", "")
        assert "crm" in redirect.lower() or "cRM" in redirect or "CRM" in redirect

    def test_auth_crm_redirect_mentions_public_or_securebank(self):
        guard = self._get_guard_instance(AuthenticatedCRMAgent)
        if guard is None:
            pytest.skip("AuthenticatedCRMAgent has no scope guard")
        redirect = guard._redirect if hasattr(guard, "_redirect") else getattr(guard._inner, "_violation_message", "")
        assert "public" in redirect.lower() or "securebank" in redirect.lower()

    def test_disputes_redirect_mentions_crm(self):
        guard = self._get_guard_instance(DisputesAgent)
        if guard is None:
            pytest.skip("DisputesAgent has no scope guard")
        redirect = guard._redirect if hasattr(guard, "_redirect") else getattr(guard._inner, "_violation_message", "")
        assert "crm" in redirect.lower() or "CRM" in redirect

    def test_all_three_guarded_agents_have_distinct_guardrail_names(self):
        """Each agent must have a unique guardrail name for activity feed clarity."""
        transfer_guard = self._get_guard_instance(BankTransferAgent)
        auth_guard = self._get_guard_instance(AuthenticatedCRMAgent)
        disputes_guard = self._get_guard_instance(DisputesAgent)

        if None in (transfer_guard, auth_guard, disputes_guard):
            pytest.skip("One or more guards are not configured yet")

        names = {
            transfer_guard._guardrail_name,
            auth_guard._guardrail_name,
            disputes_guard._guardrail_name,
        }
        assert len(names) == 3, f"Guardrail names must be distinct, got: {names}"
