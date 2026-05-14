"""Unit tests for AgentScopeGuard — keyword-based output guardrail.

Tests run the guardrail in isolation with a patched signal bus so no real
signals are emitted and no network calls are made.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("PAYLOAD_SECRET", "test-secret-abc123")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")

from lauren_ai._guardrails._base import GuardrailContext

from app.ai.guardrails.agent_scope_guard import AgentScopeGuard

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PHRASES = ("branch hour", "interest rate", "account opening")
_REDIRECT = "I can't help with that. Please ask our CRM agent."
_CTX = GuardrailContext(agent_name="TestAgent")


def _make_guard(
    phrases: tuple[str, ...] = _PHRASES,
    redirect: str = _REDIRECT,
    guardrail_name: str = "TestGuard",
    agent_name: str = "TestAgent",
) -> AgentScopeGuard:
    return AgentScopeGuard(
        off_topic_phrases=phrases,
        redirect_message=redirect,
        guardrail_name=guardrail_name,
        agent_name=agent_name,
    )


# ---------------------------------------------------------------------------
# Class 1 — TestAgentScopeGuardPassBehavior (7 tests)
# ---------------------------------------------------------------------------


class TestAgentScopeGuardPassBehavior:
    async def test_no_matching_phrase_returns_pass(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard()
            decision = await guard.check("Your balance is $500.", _CTX)
        assert decision.action == "pass"

    async def test_pass_emits_pass_signal(self):
        """When no phrase matches the guard emits a GuardrailTriggered with passed=True."""
        from app.ai.signals import GuardrailTriggered

        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard()
            await guard.check("Your balance is $500.", _CTX)
        bus.emit.assert_called_once()
        event = bus.emit.call_args[0][0]
        assert isinstance(event, GuardrailTriggered)
        assert event.passed is True

    async def test_pass_when_empty_response(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard()
            decision = await guard.check("", _CTX)
        assert decision.action == "pass"

    async def test_pass_when_phrase_not_exact_substring(self):
        # "rating" contains "rate" but not "interest rate"
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(phrases=("interest rate",))
            decision = await guard.check("Our rating system is A+.", _CTX)
        assert decision.action == "pass"

    async def test_pass_returns_guardrail_name_in_decision(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(guardrail_name="MyGuard")
            decision = await guard.check("Hello!", _CTX)
        assert decision.guardrail_name == "MyGuard"

    async def test_case_insensitive_phrase_matching_upper(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(phrases=("branch hour",))
            decision = await guard.check("BRANCH HOURS ARE 9-5.", _CTX)
        assert decision.action == "modify"  # uppercase response still triggers

    async def test_case_insensitive_phrase_matching_mixed(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(phrases=("branch hour",))
            decision = await guard.check("Branch Hours vary by location.", _CTX)
        assert decision.action == "modify"


# ---------------------------------------------------------------------------
# Class 2 — TestAgentScopeGuardBlockBehavior (10 tests)
# ---------------------------------------------------------------------------


class TestAgentScopeGuardBlockBehavior:
    async def test_matching_phrase_returns_modify(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard()
            decision = await guard.check("Branch hours are 9 AM to 5 PM.", _CTX)
        assert decision.action == "modify"

    async def test_modify_action_uses_redirect_message(self):
        redirect = "Custom redirect message."
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(redirect=redirect)
            decision = await guard.check("Our branch hour is 9 to 5.", _CTX)
        assert decision.modified_content == redirect

    async def test_signal_emitted_on_match(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard()
            await guard.check("branch hour is limited.", _CTX)
        bus.emit.assert_called_once()

    async def test_signal_guardrail_name_matches_config(self):
        from app.ai.signals import GuardrailTriggered

        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(guardrail_name="XGuard")
            await guard.check("branch hour is 9-5.", _CTX)
        event = bus.emit.call_args[0][0]
        assert isinstance(event, GuardrailTriggered)
        assert event.guardrail_name == "XGuard"

    async def test_signal_agent_name_matches_config(self):
        from app.ai.signals import GuardrailTriggered

        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(agent_name="SpecialAgent")
            await guard.check("branch hour info", _CTX)
        event = bus.emit.call_args[0][0]
        assert event.agent_name == "SpecialAgent"

    async def test_signal_violation_contains_matched_phrase(self):
        from app.ai.signals import GuardrailTriggered

        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(phrases=("interest rate",))
            await guard.check("Our interest rate is 5%.", _CTX)
        event = bus.emit.call_args[0][0]
        assert "interest rate" in event.violation

    async def test_first_matching_phrase_fires_single_signal(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(phrases=("branch hour", "interest rate"))
            # Both phrases present — only one signal emitted (first match)
            await guard.check("branch hour is 9-5 and interest rate is 5%.", _CTX)
        assert bus.emit.call_count == 1

    async def test_multiple_phrase_list_second_triggers(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(phrases=("branch hour", "interest rate", "account opening"))
            # Only second phrase present
            decision = await guard.check("The interest rate is competitive.", _CTX)
        assert decision.action == "modify"

    async def test_redirect_message_is_exact_in_modified_content(self):
        redirect = "Exact\nMultiline\nRedirect"
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(redirect=redirect)
            decision = await guard.check("branch hour question", _CTX)
        assert decision.modified_content == redirect

    async def test_action_is_modify_not_block(self):
        """Guardrail must use action='modify' — 'block' would crash the stream."""
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard()
            decision = await guard.check("branch hour is 9-5.", _CTX)
        assert decision.action == "modify"
        assert decision.action != "block"


# ---------------------------------------------------------------------------
# Class 3 — TestAgentScopeGuardEdgeCases (8 tests)
# ---------------------------------------------------------------------------


class TestAgentScopeGuardEdgeCases:
    async def test_signal_emit_exception_does_not_crash_check(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock(side_effect=RuntimeError("bus crashed"))
            guard = _make_guard()
            # Should not raise even though signal_bus.emit throws
            decision = await guard.check("branch hour is 9-5.", _CTX)
        # Decision is still returned despite the exception
        assert decision is not None

    async def test_multiple_phrases_matches_second_one(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(phrases=("xyz_not_present", "interest rate"))
            decision = await guard.check("The interest rate is 5%.", _CTX)
        assert decision.action == "modify"

    async def test_phrase_matches_as_substring_of_longer_word(self):
        """'loan' in phrase list matches 'loan application'."""
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(phrases=("loan",))
            decision = await guard.check("We offer loan products.", _CTX)
        assert decision.action == "modify"

    async def test_guardrail_name_in_decision_on_trigger(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(guardrail_name="NamedGuard")
            decision = await guard.check("branch hour question", _CTX)
        assert decision.guardrail_name == "NamedGuard"

    async def test_whitespace_in_response_does_not_prevent_match(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(phrases=("branch hour",))
            decision = await guard.check("  branch hour  starts at 9 AM.", _CTX)
        assert decision.action == "modify"

    async def test_unicode_response_handled_gracefully(self):
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(phrases=("interest rate",))
            decision = await guard.check("L'intérêt (interest rate) est 5%.", _CTX)
        assert decision.action == "modify"

    async def test_empty_phrases_tuple_never_fires_no_signal(self):
        """With no phrases, there is nothing to evaluate — no signal emitted at all."""
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(phrases=())
            decision = await guard.check("branch hour interest rate anything", _CTX)
        assert decision.action == "pass"
        # Empty phrase list → no evaluation → no signal (not even a pass signal)
        bus.emit.assert_not_called()

    async def test_redirect_with_special_markdown_chars_preserved(self):
        redirect = "I can't help.\n\n*(Say **yes** to transfer.)*"
        with patch("app.ai.guardrails.agent_scope_guard._default_bus") as bus:
            bus.emit = AsyncMock()
            guard = _make_guard(redirect=redirect)
            decision = await guard.check("branch hour info", _CTX)
        assert decision.modified_content == redirect
