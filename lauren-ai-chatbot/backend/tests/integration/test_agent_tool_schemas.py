# NOTE: Do NOT add `from __future__ import annotations` to this file.
"""Regression tests for agent tool-schema isolation.

Each `@agent()`-decorated class in the banking chatbot declares its tool set
via `@use_tools(...)`.  The runner's `_get_tool_schemas(meta)` builds the
list of JSON schemas the LLM sees — this list MUST contain exactly the tools
the agent declared, with NO leakage from sibling agents' modules.

These tests build the full Lauren application via `LaurenFactory.create`,
resolve each agent's runner from the DI container, and compare:

* `runner._get_tool_schemas(agent_meta)` (the schemas the LLM actually sees)
* the tool names derived from the agent class's `@use_tools(...)` declaration

The two sets must match exactly.  Cross-agent leakage tests assert that
tools owned by sibling modules (e.g. ``ApprovalTool`` for the Transfer
agent) do NOT appear in another agent's schema list (e.g. the Disputes
agent must never see ``ApprovalTool``).
"""

import asyncio
import os
from typing import get_origin

import pytest

os.environ.setdefault("PAYLOAD_SECRET", "tool-schema-test-secret")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy-key-for-tests")
os.environ.setdefault("PORT", "8004")

from lauren_ai._agents import AGENT_META, USE_TOOLS_META  # noqa: E402
from lauren_ai._tools import TOOL_META  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():
    """Build the full Lauren app once per module."""
    from app.app_module import AppModule
    from app.interceptors.timing_interceptor import TimingInterceptor
    from app.middlewares.cors_middleware import CorsMiddleware
    from app.middlewares.logging_middleware import LoggingMiddleware
    from lauren import LaurenFactory

    return LaurenFactory.create(
        AppModule,
        global_middlewares=[CorsMiddleware, LoggingMiddleware],
        global_interceptors=[TimingInterceptor],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_runner(app, runner_cls):
    """Resolve a runner instance from the DI container."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(app.container.resolve(runner_cls))
    finally:
        loop.close()


def _expected_tool_names(agent_cls) -> list[str]:
    """Return the snake_case tool names from `@use_tools(...)`, in order.

    Mirrors the runner's own iteration logic: each tool item's TOOL_META
    name is the canonical identifier the LLM sees.  For generic aliases
    (``HandoffTo[A, B]``) we follow the same `get_origin()` fallback the
    framework uses internally.
    """
    tool_classes = getattr(agent_cls, USE_TOOLS_META, ())
    names: list[str] = []
    for tc in tool_classes:
        origin = get_origin(tc) or tc
        meta = getattr(origin, TOOL_META, None) or getattr(tc, TOOL_META, None)
        if meta is not None:
            names.append(meta.name)
    return names


def _schema_names(runner, agent_cls) -> list[str]:
    """Return the tool names actually present in the schemas the runner emits."""
    agent_meta = getattr(agent_cls, AGENT_META)
    schemas = runner._get_tool_schemas(agent_meta)
    return [s["name"] for s in schemas]


# ---------------------------------------------------------------------------
# Per-agent: schemas == declared @use_tools
# ---------------------------------------------------------------------------


class TestUnauthCRMSchemaMatchesDeclared:
    """`@use_tools(CheckAuthenticationTool, HandoffToAuthenticatedCRM)`."""

    def test_schemas_match_declared(self, app):
        from app.ai.agents.banking_delegation import UnauthCRMRunner
        from app.ai.agents.unauth_crm_agent import UnauthenticatedCRMAgent

        runner = _resolve_runner(app, UnauthCRMRunner)
        actual = sorted(_schema_names(runner, UnauthenticatedCRMAgent))
        expected = sorted(_expected_tool_names(UnauthenticatedCRMAgent))

        assert actual == expected, f"UnauthCRM schemas {actual!r} != declared {expected!r}"

    def test_schema_count_matches_declared(self, app):
        from app.ai.agents.banking_delegation import UnauthCRMRunner
        from app.ai.agents.unauth_crm_agent import UnauthenticatedCRMAgent

        runner = _resolve_runner(app, UnauthCRMRunner)
        actual = _schema_names(runner, UnauthenticatedCRMAgent)
        expected = _expected_tool_names(UnauthenticatedCRMAgent)

        assert len(actual) == len(expected) == 2


class TestAuthCRMSchemaMatchesDeclared:
    """`@use_tools(GetBalanceTool, GetTransactionHistoryTool, CheckAuthenticationTool, HandoffTo)`."""

    def test_schemas_match_declared(self, app):
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent
        from app.ai.agents.banking_delegation import AuthCRMRunner

        runner = _resolve_runner(app, AuthCRMRunner)
        actual = sorted(_schema_names(runner, AuthenticatedCRMAgent))
        expected = sorted(_expected_tool_names(AuthenticatedCRMAgent))

        assert actual == expected, f"AuthCRM schemas {actual!r} != declared {expected!r}"

    def test_schema_count_matches_declared(self, app):
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent
        from app.ai.agents.banking_delegation import AuthCRMRunner

        runner = _resolve_runner(app, AuthCRMRunner)
        actual = _schema_names(runner, AuthenticatedCRMAgent)
        expected = _expected_tool_names(AuthenticatedCRMAgent)

        assert len(actual) == len(expected) == 4


class TestTransferSchemaMatchesDeclared:
    """`@use_tools(ApprovalTool, TransferFundsTool, CheckAuthenticationTool, HandoffTo)`."""

    def test_schemas_match_declared(self, app):
        from app.ai.agents.banking_delegation import TransferAgentRunner
        from app.ai.agents.transfer_agent import BankTransferAgent

        runner = _resolve_runner(app, TransferAgentRunner)
        actual = sorted(_schema_names(runner, BankTransferAgent))
        expected = sorted(_expected_tool_names(BankTransferAgent))

        assert actual == expected, f"Transfer schemas {actual!r} != declared {expected!r}"

    def test_schema_count_matches_declared(self, app):
        from app.ai.agents.banking_delegation import TransferAgentRunner
        from app.ai.agents.transfer_agent import BankTransferAgent

        runner = _resolve_runner(app, TransferAgentRunner)
        actual = _schema_names(runner, BankTransferAgent)
        expected = _expected_tool_names(BankTransferAgent)

        assert len(actual) == len(expected) == 4


class TestDisputesSchemaMatchesDeclared:
    """`@use_tools(GetBalanceTool, GetTransactionHistoryTool, CheckAuthenticationTool, HandoffTo)`."""

    def test_schemas_match_declared(self, app):
        from app.ai.agents.banking_delegation import DisputesAgentRunner
        from app.ai.agents.disputes_agent import DisputesAgent

        runner = _resolve_runner(app, DisputesAgentRunner)
        actual = sorted(_schema_names(runner, DisputesAgent))
        expected = sorted(_expected_tool_names(DisputesAgent))

        assert actual == expected, f"Disputes schemas {actual!r} != declared {expected!r}"

    def test_schema_count_matches_declared(self, app):
        from app.ai.agents.banking_delegation import DisputesAgentRunner
        from app.ai.agents.disputes_agent import DisputesAgent

        runner = _resolve_runner(app, DisputesAgentRunner)
        actual = _schema_names(runner, DisputesAgent)
        expected = _expected_tool_names(DisputesAgent)

        assert len(actual) == len(expected) == 4


# ---------------------------------------------------------------------------
# Cross-agent leakage
# ---------------------------------------------------------------------------


class TestNoCrossAgentLeakage:
    """An agent's schema must not include tools owned by a sibling agent.

    The four agents share a process and DI graph.  The runner's tool map
    is per-module, but a regression in `AgentModule.for_root()` could
    accidentally surface a tool from one module in another module's
    schema list.  These tests pin the contract.
    """

    # ─── Tool ownership map (canonical names from snake_case conversion) ────
    _APPROVAL_TOOL = "approval_tool"
    _TRANSFER_FUNDS_TOOL = "transfer_funds_tool"
    _GET_BALANCE_TOOL = "get_balance_tool"
    _GET_TRANSACTION_HISTORY_TOOL = "get_transaction_history_tool"

    def test_unauth_crm_does_not_see_balance_or_transactions(self, app):
        from app.ai.agents.banking_delegation import UnauthCRMRunner
        from app.ai.agents.unauth_crm_agent import UnauthenticatedCRMAgent

        runner = _resolve_runner(app, UnauthCRMRunner)
        names = set(_schema_names(runner, UnauthenticatedCRMAgent))

        forbidden = {
            self._GET_BALANCE_TOOL,
            self._GET_TRANSACTION_HISTORY_TOOL,
            self._APPROVAL_TOOL,
            self._TRANSFER_FUNDS_TOOL,
        }
        leaked = names & forbidden
        assert not leaked, f"UnauthCRM agent leaked sibling tools: {sorted(leaked)}"

    def test_auth_crm_does_not_see_approval_or_transfer(self, app):
        """AuthCRM hands off to TransferAgent — it must NOT call those tools itself."""
        from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent
        from app.ai.agents.banking_delegation import AuthCRMRunner

        runner = _resolve_runner(app, AuthCRMRunner)
        names = set(_schema_names(runner, AuthenticatedCRMAgent))

        forbidden = {self._APPROVAL_TOOL, self._TRANSFER_FUNDS_TOOL}
        leaked = names & forbidden
        assert not leaked, f"AuthCRM agent leaked Transfer-only tools: {sorted(leaked)}"

    def test_transfer_does_not_see_balance_or_transaction_history(self, app):
        """Transfer agent only executes transfers — it must NOT see read-only banking tools."""
        from app.ai.agents.banking_delegation import TransferAgentRunner
        from app.ai.agents.transfer_agent import BankTransferAgent

        runner = _resolve_runner(app, TransferAgentRunner)
        names = set(_schema_names(runner, BankTransferAgent))

        forbidden = {
            self._GET_BALANCE_TOOL,
            self._GET_TRANSACTION_HISTORY_TOOL,
        }
        leaked = names & forbidden
        assert not leaked, f"Transfer agent leaked read-only banking tools: {sorted(leaked)}"

    def test_disputes_does_not_see_approval_or_transfer(self, app):
        """Disputes investigates — it must NOT have direct access to write tools."""
        from app.ai.agents.banking_delegation import DisputesAgentRunner
        from app.ai.agents.disputes_agent import DisputesAgent

        runner = _resolve_runner(app, DisputesAgentRunner)
        names = set(_schema_names(runner, DisputesAgent))

        forbidden = {self._APPROVAL_TOOL, self._TRANSFER_FUNDS_TOOL}
        leaked = names & forbidden
        assert not leaked, f"Disputes agent leaked write tools: {sorted(leaked)}"


# ---------------------------------------------------------------------------
# Schema invariants
# ---------------------------------------------------------------------------


class TestSchemaShape:
    """Each schema in the list must be a JSON Schema with at least name + input_schema."""

    @pytest.mark.parametrize(
        "runner_cls_path,agent_cls_path",
        [
            (
                "app.ai.agents.banking_delegation:UnauthCRMRunner",
                "app.ai.agents.unauth_crm_agent:UnauthenticatedCRMAgent",
            ),
            (
                "app.ai.agents.banking_delegation:AuthCRMRunner",
                "app.ai.agents.auth_crm_agent:AuthenticatedCRMAgent",
            ),
            (
                "app.ai.agents.banking_delegation:TransferAgentRunner",
                "app.ai.agents.transfer_agent:BankTransferAgent",
            ),
            (
                "app.ai.agents.banking_delegation:DisputesAgentRunner",
                "app.ai.agents.disputes_agent:DisputesAgent",
            ),
        ],
    )
    def test_every_schema_has_a_name(self, app, runner_cls_path, agent_cls_path):
        """No schema in any agent's list may be missing a ``name`` field."""
        import importlib

        runner_mod, runner_cls_name = runner_cls_path.split(":")
        agent_mod, agent_cls_name = agent_cls_path.split(":")
        runner_cls = getattr(importlib.import_module(runner_mod), runner_cls_name)
        agent_cls = getattr(importlib.import_module(agent_mod), agent_cls_name)

        runner = _resolve_runner(app, runner_cls)
        agent_meta = getattr(agent_cls, AGENT_META)
        schemas = runner._get_tool_schemas(agent_meta)

        for i, schema in enumerate(schemas):
            assert "name" in schema, f"{agent_cls_name} schema #{i} missing 'name' field: {schema!r}"
            assert isinstance(schema["name"], str)
            assert schema["name"], f"{agent_cls_name} schema #{i} has empty name"
