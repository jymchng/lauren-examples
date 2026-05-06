"""Unit tests for banking agent runner DI tokens."""

from __future__ import annotations

from app.ai.banking_delegation import AuthCRMRunner, DisputesAgentRunner, TransferAgentRunner, UnauthCRMRunner
from lauren_ai import AgentRunnerBase


class TestRunnerDITokens:
    def test_unauth_crm_runner_is_agent_runner_base_subclass(self):
        assert issubclass(UnauthCRMRunner, AgentRunnerBase)

    def test_auth_crm_runner_is_agent_runner_base_subclass(self):
        assert issubclass(AuthCRMRunner, AgentRunnerBase)

    def test_transfer_agent_runner_is_agent_runner_base_subclass(self):
        assert issubclass(TransferAgentRunner, AgentRunnerBase)

    def test_disputes_agent_runner_is_agent_runner_base_subclass(self):
        assert issubclass(DisputesAgentRunner, AgentRunnerBase)

    def test_runner_tokens_are_distinct(self):
        assert UnauthCRMRunner is not AuthCRMRunner
        assert AuthCRMRunner is not TransferAgentRunner
        assert UnauthCRMRunner is not TransferAgentRunner
        assert DisputesAgentRunner is not AuthCRMRunner
        assert DisputesAgentRunner is not TransferAgentRunner

    def test_runners_have_injectable_meta(self):
        from lauren._di import INJECTABLE_META

        assert hasattr(UnauthCRMRunner, INJECTABLE_META)
        assert hasattr(AuthCRMRunner, INJECTABLE_META)
        assert hasattr(TransferAgentRunner, INJECTABLE_META)
        assert hasattr(DisputesAgentRunner, INJECTABLE_META)
