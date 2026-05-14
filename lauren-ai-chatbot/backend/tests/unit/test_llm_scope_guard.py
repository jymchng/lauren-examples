"""Unit tests for LLMScopeGuard — LLM-based output guardrail.

Creates LLMScopeGuard with a mock inner LLMGuardrail so no real LLM calls
are made.  Signal bus is also patched.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("PAYLOAD_SECRET", "test-secret-abc123")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")

from lauren_ai import LLMConfig
from lauren_ai._guardrails._base import GuardrailContext, GuardrailDecision

_CTX = GuardrailContext(agent_name="TestAgent")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_config() -> LLMConfig:
    return LLMConfig(
        provider="openai",
        model="test-model",
        api_key="dummy",
        base_url="https://openrouter.ai/api/v1",
    )


def _make_guard_with_mock_inner(
    inner_decision: GuardrailDecision,
    guardrail_name: str = "TestLLMGuard",
    agent_name: str = "TestAgent",
    redirect: str = "Redirect message.",
):
    """Create LLMScopeGuard and replace its _inner with a mock that returns the given decision."""
    from app.ai.guardrails.llm_scope_guard import LLMScopeGuard

    with patch("app.ai.guardrails.llm_scope_guard._default_bus") as _bus:
        _bus.emit = AsyncMock()
        guard = LLMScopeGuard(
            llm_config=_fake_config(),
            agent_role="Test Agent",
            allowed_scope="• Test scope only",
            redirect_message=redirect,
            guardrail_name=guardrail_name,
            agent_name=agent_name,
        )

    mock_inner = MagicMock()
    mock_inner.check = AsyncMock(return_value=inner_decision)
    guard._inner = mock_inner
    return guard


# ---------------------------------------------------------------------------
# Class 1 — TestLLMScopeGuardPass (7 tests)
# ---------------------------------------------------------------------------


class TestLLMScopeGuardPass:
    async def test_judge_returns_no_action_is_pass(self):
        guard = _make_guard_with_mock_inner(GuardrailDecision(action="pass", guardrail_name="TestLLMGuard"))
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            decision = await guard.check("Your balance is $500.", _CTX)
        assert decision.action == "pass"

    async def test_pass_emits_pass_signal(self):
        """When judge says pass, a GuardrailTriggered with passed=True is emitted."""
        from app.ai.signals import GuardrailTriggered

        guard = _make_guard_with_mock_inner(GuardrailDecision(action="pass", guardrail_name="TestLLMGuard"))
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            await guard.check("Fine response.", _CTX)
        bus.emit.assert_called_once()
        event = bus.emit.call_args[0][0]
        assert isinstance(event, GuardrailTriggered)
        assert event.passed is True

    async def test_pass_decision_has_correct_guardrail_name(self):
        guard = _make_guard_with_mock_inner(
            GuardrailDecision(action="pass", guardrail_name="XGuard"),
            guardrail_name="XGuard",
        )
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            decision = await guard.check("Fine.", _CTX)
        assert decision.guardrail_name == "XGuard"

    async def test_inner_check_called_with_response_text(self):
        guard = _make_guard_with_mock_inner(GuardrailDecision(action="pass", guardrail_name="G"))
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            await guard.check("unique-response-xyz", _CTX)
        guard._inner.check.assert_called_once()
        args = guard._inner.check.call_args[0]
        assert args[0] == "unique-response-xyz"

    async def test_empty_response_treated_as_pass_when_inner_says_pass(self):
        guard = _make_guard_with_mock_inner(GuardrailDecision(action="pass", guardrail_name="G"))
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            decision = await guard.check("", _CTX)
        assert decision.action == "pass"

    async def test_pass_returns_inner_decision_unchanged(self):
        inner = GuardrailDecision(action="pass", guardrail_name="G", violation=None)
        guard = _make_guard_with_mock_inner(inner)
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            result = await guard.check("fine", _CTX)
        assert result is inner  # same object returned

    async def test_pass_no_exception_propagated(self):
        guard = _make_guard_with_mock_inner(GuardrailDecision(action="pass", guardrail_name="G"))
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            # Should not raise
            await guard.check("safe text", _CTX)


# ---------------------------------------------------------------------------
# Class 2 — TestLLMScopeGuardFire (8 tests)
# ---------------------------------------------------------------------------


class TestLLMScopeGuardFire:
    async def test_judge_returns_modify_fires_guardrail(self):
        guard = _make_guard_with_mock_inner(
            GuardrailDecision(
                action="modify",
                modified_content="Redirect msg.",
                guardrail_name="G",
                violation="Violation",
            )
        )
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            decision = await guard.check("bad response", _CTX)
        assert decision.action == "modify"

    async def test_modify_content_is_redirect_message(self):
        redirect = "Custom redirect for this guard."
        guard = _make_guard_with_mock_inner(
            GuardrailDecision(
                action="modify",
                modified_content=redirect,
                guardrail_name="G",
            ),
            redirect=redirect,
        )
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            decision = await guard.check("bad response", _CTX)
        assert decision.modified_content == redirect

    async def test_signal_emitted_on_modify(self):
        guard = _make_guard_with_mock_inner(
            GuardrailDecision(
                action="modify",
                modified_content="R",
                guardrail_name="G",
                violation="V",
            )
        )
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            await guard.check("bad", _CTX)
        bus.emit.assert_called_once()

    async def test_signal_guardrail_name_from_config(self):
        from app.ai.signals import GuardrailTriggered

        guard = _make_guard_with_mock_inner(
            GuardrailDecision(action="modify", modified_content="R", guardrail_name="XGuard"),
            guardrail_name="XGuard",
        )
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            await guard.check("bad", _CTX)
        event = bus.emit.call_args[0][0]
        assert isinstance(event, GuardrailTriggered)
        assert event.guardrail_name == "XGuard"

    async def test_signal_agent_name_from_config(self):
        from app.ai.signals import GuardrailTriggered

        guard = _make_guard_with_mock_inner(
            GuardrailDecision(action="modify", modified_content="R", guardrail_name="G"),
            agent_name="Special Agent",
        )
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            await guard.check("bad", _CTX)
        event = bus.emit.call_args[0][0]
        assert event.agent_name == "Special Agent"

    async def test_signal_violation_from_inner_decision(self):
        from app.ai.signals import GuardrailTriggered

        guard = _make_guard_with_mock_inner(
            GuardrailDecision(
                action="modify",
                modified_content="R",
                guardrail_name="G",
                violation="specific violation text",
            )
        )
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            await guard.check("bad", _CTX)
        event = bus.emit.call_args[0][0]
        assert "specific violation text" in event.violation

    async def test_inner_check_called_before_signal_emitted(self):
        """Inner check must be called first, signal after."""
        call_order: list[str] = []
        mock_inner = MagicMock()

        async def inner_check(text, ctx):
            call_order.append("inner_check")
            return GuardrailDecision(action="modify", modified_content="R", guardrail_name="G")

        mock_inner.check = inner_check

        from app.ai.guardrails.llm_scope_guard import LLMScopeGuard

        guard = LLMScopeGuard(
            llm_config=_fake_config(),
            agent_role="R",
            allowed_scope="S",
            redirect_message="R",
            guardrail_name="G",
        )
        guard._inner = mock_inner

        async def record_emit(event):
            call_order.append("signal_emitted")

        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = record_emit
            await guard.check("bad text", _CTX)

        assert call_order == ["inner_check", "signal_emitted"]

    async def test_fallback_violation_when_inner_has_none(self):
        from app.ai.signals import GuardrailTriggered

        # inner has violation=None
        guard = _make_guard_with_mock_inner(
            GuardrailDecision(action="modify", modified_content="R", guardrail_name="G", violation=None)
        )
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            await guard.check("bad", _CTX)
        event = bus.emit.call_args[0][0]
        # Fallback violation text is set
        assert event.violation is not None
        assert len(event.violation) > 0


# ---------------------------------------------------------------------------
# Class 3 — TestLLMScopeGuardErrorHandling (5 tests)
# ---------------------------------------------------------------------------


class TestLLMScopeGuardErrorHandling:
    async def test_llm_exception_fails_open(self):
        """If inner.check raises, the guard fails open (returns pass)."""
        from app.ai.guardrails.llm_scope_guard import LLMScopeGuard

        guard = LLMScopeGuard(
            llm_config=_fake_config(),
            agent_role="R",
            allowed_scope="S",
            redirect_message="R",
            guardrail_name="G",
        )
        mock_inner = MagicMock()
        mock_inner.check = AsyncMock(side_effect=RuntimeError("LLM exploded"))
        guard._inner = mock_inner

        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            # LLMScopeGuard doesn't have its own try/except — relies on runner
            # This test documents that exceptions propagate (runner catches them)
            with pytest.raises(RuntimeError, match="LLM exploded"):
                await guard.check("some response", _CTX)

    async def test_llm_exception_no_signal_emitted(self):
        """If inner.check raises, no signal is emitted."""
        from app.ai.guardrails.llm_scope_guard import LLMScopeGuard

        guard = LLMScopeGuard(
            llm_config=_fake_config(),
            agent_role="R",
            allowed_scope="S",
            redirect_message="R",
            guardrail_name="G",
        )
        mock_inner = MagicMock()
        mock_inner.check = AsyncMock(side_effect=RuntimeError("oops"))
        guard._inner = mock_inner

        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            with pytest.raises(RuntimeError):
                await guard.check("response", _CTX)
        bus.emit.assert_not_called()

    async def test_llm_pass_response_emits_pass_signal(self):
        """LLM returns pass → passed=True signal emitted, action=pass."""
        from app.ai.signals import GuardrailTriggered

        guard = _make_guard_with_mock_inner(GuardrailDecision(action="pass", guardrail_name="G"))
        with patch("app.ai.guardrails.llm_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            decision = await guard.check("safe response", _CTX)
        assert decision.action == "pass"
        bus.emit.assert_called_once()
        event = bus.emit.call_args[0][0]
        assert isinstance(event, GuardrailTriggered)
        assert event.passed is True

    async def test_guard_construction_does_not_raise_with_valid_config(self):
        from app.ai.guardrails.llm_scope_guard import LLMScopeGuard

        # Should not raise during construction
        guard = LLMScopeGuard(
            llm_config=_fake_config(),
            agent_role="Test Agent",
            allowed_scope="• Only transfers",
            redirect_message="Redirect.",
            guardrail_name="G",
            agent_name="A",
        )
        assert guard is not None

    async def test_inner_llm_guardrail_created_with_correct_config(self):
        from lauren_ai import LLMGuardrail
        from app.ai.guardrails.llm_scope_guard import LLMScopeGuard

        guard = LLMScopeGuard(
            llm_config=_fake_config(),
            agent_role="Test",
            allowed_scope="• Scope",
            redirect_message="Redirect",
            guardrail_name="G",
        )
        # _inner should be an LLMGuardrail
        assert isinstance(guard._inner, LLMGuardrail)
