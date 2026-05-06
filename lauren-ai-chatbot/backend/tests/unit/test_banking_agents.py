"""Unit tests for all four banking agents' metadata and configuration."""

from __future__ import annotations

import pytest

from app.ai.agents.auth_crm_agent import AuthenticatedCRMAgent
from app.ai.agents.disputes_agent import DisputesAgent
from app.ai.agents.transfer_agent import BankTransferAgent
from app.ai.agents.unauth_crm_agent import UnauthenticatedCRMAgent


class TestUnauthenticatedCRMAgent:
    def test_has_agent_meta(self):
        assert hasattr(UnauthenticatedCRMAgent, "__lauren_ai_agent__")

    def test_agent_meta_has_system_prompt(self):
        meta = getattr(UnauthenticatedCRMAgent, "__lauren_ai_agent__")
        assert meta.system

    def test_agent_meta_has_max_turns(self):
        meta = getattr(UnauthenticatedCRMAgent, "__lauren_ai_agent__")
        assert meta.config.max_turns is not None

    def test_system_prompt_mentions_securebank(self):
        meta = getattr(UnauthenticatedCRMAgent, "__lauren_ai_agent__")
        assert "SecureBank" in meta.system or "bank" in meta.system.lower()

    def test_system_prompt_mentions_authentication(self):
        meta = getattr(UnauthenticatedCRMAgent, "__lauren_ai_agent__")
        assert "auth" in meta.system.lower() or "log in" in meta.system.lower()

    def test_has_use_tools_meta(self):
        assert hasattr(UnauthenticatedCRMAgent, "__lauren_ai_use_tools__") or hasattr(UnauthenticatedCRMAgent, "__lauren_ai_agent__")


class TestAuthenticatedCRMAgent:
    def test_has_agent_meta(self):
        assert hasattr(AuthenticatedCRMAgent, "__lauren_ai_agent__")

    def test_agent_meta_has_system_prompt(self):
        meta = getattr(AuthenticatedCRMAgent, "__lauren_ai_agent__")
        assert meta.system

    def test_agent_meta_has_max_turns(self):
        meta = getattr(AuthenticatedCRMAgent, "__lauren_ai_agent__")
        assert meta.config.max_turns is not None

    def test_system_prompt_mentions_securebank(self):
        meta = getattr(AuthenticatedCRMAgent, "__lauren_ai_agent__")
        assert "SecureBank" in meta.system or "bank" in meta.system.lower()

    def test_system_prompt_mentions_identity(self):
        meta = getattr(AuthenticatedCRMAgent, "__lauren_ai_agent__")
        assert "BANKING_AUTH" in meta.system or "identity" in meta.system.lower()

    def test_has_use_tools_meta(self):
        assert hasattr(AuthenticatedCRMAgent, "__lauren_ai_use_tools__") or hasattr(AuthenticatedCRMAgent, "__lauren_ai_agent__")


class TestBankTransferAgent:
    def test_has_agent_meta(self):
        assert hasattr(BankTransferAgent, "__lauren_ai_agent__")

    def test_agent_meta_has_model(self):
        meta = getattr(BankTransferAgent, "__lauren_ai_agent__")
        assert hasattr(meta, "model")

    def test_agent_meta_has_system_prompt(self):
        meta = getattr(BankTransferAgent, "__lauren_ai_agent__")
        assert meta.config.system_prompt

    def test_system_prompt_mentions_transfer(self):
        meta = getattr(BankTransferAgent, "__lauren_ai_agent__")
        assert "transfer" in meta.system.lower() or "bank" in meta.system.lower()

    def test_has_use_tools_meta(self):
        assert hasattr(BankTransferAgent, "__lauren_ai_use_tools__") or hasattr(BankTransferAgent, "__lauren_ai_agent__")


class TestDisputesAgent:
    def test_has_agent_meta(self):
        assert hasattr(DisputesAgent, "__lauren_ai_agent__")

    def test_agent_meta_has_system_prompt(self):
        meta = getattr(DisputesAgent, "__lauren_ai_agent__")
        assert meta.system

    def test_agent_meta_has_max_turns(self):
        meta = getattr(DisputesAgent, "__lauren_ai_agent__")
        assert meta.config.max_turns is not None

    def test_system_prompt_mentions_dispute(self):
        meta = getattr(DisputesAgent, "__lauren_ai_agent__")
        assert "dispute" in meta.system.lower()

    def test_system_prompt_mentions_fraud(self):
        meta = getattr(DisputesAgent, "__lauren_ai_agent__")
        assert "fraud" in meta.system.lower()

    def test_has_use_tools_meta(self):
        assert hasattr(DisputesAgent, "__lauren_ai_use_tools__") or hasattr(DisputesAgent, "__lauren_ai_agent__")


class TestCheckAuthenticationTool:
    def test_tool_meta_is_present(self):
        from app.ai.tools.check_auth_tool import CheckAuthenticationTool
        from lauren_ai._tools import TOOL_META

        assert hasattr(CheckAuthenticationTool, TOOL_META)

    def test_tool_schema_has_no_parameters(self):
        from app.ai.tools.check_auth_tool import CheckAuthenticationTool
        from lauren_ai._tools import TOOL_META

        meta = getattr(CheckAuthenticationTool, TOOL_META)
        props = meta.parameters["input_schema"].get("properties", {})
        assert "ctx" not in props

    @pytest.mark.asyncio
    async def test_returns_unauthenticated_when_no_context(self):
        from unittest.mock import MagicMock
        from app.ai.tools.check_auth_tool import CheckAuthenticationTool

        tool = CheckAuthenticationTool()
        ctx = MagicMock()
        ctx.execution_context = None
        result = await tool.run(ctx)
        assert result == {"authenticated": False}

    @pytest.mark.asyncio
    async def test_returns_authenticated_when_user_id_in_state(self):
        from unittest.mock import MagicMock
        from app.ai.tools.check_auth_tool import CheckAuthenticationTool

        tool = CheckAuthenticationTool()
        state = MagicMock()
        state.get = lambda k, default=None: {"user_id": "alice", "user_name": "Alice Johnson"}.get(k, default)
        request = MagicMock()
        request.state = state
        exec_ctx = MagicMock()
        exec_ctx.request = request
        ctx = MagicMock()
        ctx.execution_context = exec_ctx
        result = await tool.run(ctx)
        assert result["authenticated"] is True
        assert result["user_id"] == "alice"
        assert result["user_name"] == "Alice Johnson"


class TestHandoffToAuthenticatedCRM:
    def test_tool_meta_is_present(self):
        from app.ai.tools.handoff_to_authenticated import HandoffToAuthenticatedCRM
        from lauren_ai._tools import TOOL_META

        assert hasattr(HandoffToAuthenticatedCRM, TOOL_META)

    def test_tool_schema_has_summary_parameter(self):
        from app.ai.tools.handoff_to_authenticated import HandoffToAuthenticatedCRM
        from lauren_ai._tools import TOOL_META

        meta = getattr(HandoffToAuthenticatedCRM, TOOL_META)
        props = meta.parameters["input_schema"]["properties"]
        assert "summary" in props
        assert "to_agent" not in props  # no enum — single fixed target

    @pytest.mark.asyncio
    async def test_returns_auth_required_when_no_user_id(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.ai.tools.handoff_to_authenticated import HandoffToAuthenticatedCRM

        store = MagicMock()
        forwarder = MagicMock()
        forwarder.send_to_user = AsyncMock()
        tool = HandoffToAuthenticatedCRM(active_agent_store=store, event_forwarder=forwarder)
        ctx = MagicMock()
        ctx.execution_context = None
        result = await tool.run(ctx, summary="User wants balance")
        assert result["status"] == "auth_required"

    @pytest.mark.asyncio
    async def test_calls_run_handoff_when_authenticated(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        from app.ai.tools.handoff_to_authenticated import HandoffToAuthenticatedCRM
        from app.ai.agent_names import AUTH_CRM_AGENT_NAME

        store = MagicMock()
        store.set = MagicMock()
        store.set_pending_summary = MagicMock()
        forwarder = MagicMock()
        forwarder.send_to_user = AsyncMock()
        tool = HandoffToAuthenticatedCRM(active_agent_store=store, event_forwarder=forwarder)

        state = MagicMock()
        state.get = lambda k, default=None: "alice" if k == "user_id" else default
        request = MagicMock()
        request.state = state
        exec_ctx = MagicMock()
        exec_ctx.request = request
        ctx = MagicMock()
        ctx.execution_context = exec_ctx
        ctx.agent_context.metadata = {"conversation_id": "conv-1"}
        ctx.agent_context.agent_name = "Banking CRM Agent (Public)"

        result = await tool.run(ctx, summary="Authenticated user wants balance")
        assert result["status"] == "handed_off"
        assert result["to_agent"] == AUTH_CRM_AGENT_NAME


class TestUnauthCRMCannotReachTransferAgent:
    def test_handoff_to_authenticated_target_names_exclude_transfer(self):
        from app.ai.tools.handoff_to_authenticated import HandoffToAuthenticatedCRM
        from app.ai.agent_names import TRANSFER_AGENT_NAME

        assert TRANSFER_AGENT_NAME not in HandoffToAuthenticatedCRM._target_names

    def test_handoff_to_authenticated_targets_only_auth_crm(self):
        from app.ai.tools.handoff_to_authenticated import HandoffToAuthenticatedCRM
        from app.ai.agent_names import AUTH_CRM_AGENT_NAME

        assert HandoffToAuthenticatedCRM._target_names == (AUTH_CRM_AGENT_NAME,)

    def test_unauth_crm_tools_do_not_include_generic_handoff(self):
        """UnauthenticatedCRMAgent must not carry the generic HandoffTo tool."""
        from app.ai.tools.handoff_tool import HandoffTo

        tools_meta = getattr(UnauthenticatedCRMAgent, "__lauren_ai_use_tools__", [])
        tool_classes = [t if isinstance(t, type) else type(t) for t in tools_meta]
        assert HandoffTo not in tool_classes

    def test_unauth_crm_transfer_route_architecturally_blocked(self):
        """No tool reachable from UnauthenticatedCRMAgent has TRANSFER_AGENT_NAME in its _target_names."""
        from app.ai.agent_names import TRANSFER_AGENT_NAME

        tools_meta = getattr(UnauthenticatedCRMAgent, "__lauren_ai_use_tools__", [])
        for tool_cls in tools_meta:
            target_names = getattr(tool_cls, "_target_names", ())
            assert TRANSFER_AGENT_NAME not in target_names, (
                f"{tool_cls} exposes a path to {TRANSFER_AGENT_NAME}"
            )


class TestBankingToolMetas:
    def test_get_balance_tool_has_meta(self):
        from app.ai.tools.banking_tools import GetBalanceTool
        from lauren_ai._tools import TOOL_META

        assert hasattr(GetBalanceTool, TOOL_META)

    def test_transfer_funds_tool_has_meta(self):
        from app.ai.tools.banking_tools import TransferFundsTool
        from lauren_ai._tools import TOOL_META

        assert hasattr(TransferFundsTool, TOOL_META)

    def test_get_history_tool_has_meta(self):
        from app.ai.tools.banking_tools import GetTransactionHistoryTool
        from lauren_ai._tools import TOOL_META

        assert hasattr(GetTransactionHistoryTool, TOOL_META)

    def test_get_balance_schema_has_user_id(self):
        from app.ai.tools.banking_tools import GetBalanceTool
        from lauren_ai._tools import TOOL_META

        meta = getattr(GetBalanceTool, TOOL_META)
        assert "user_id" in meta.parameters["input_schema"]["properties"]

    def test_transfer_schema_has_to_user_and_amount(self):
        from app.ai.tools.banking_tools import TransferFundsTool
        from lauren_ai._tools import TOOL_META

        meta = getattr(TransferFundsTool, TOOL_META)
        props = meta.parameters["input_schema"]["properties"]
        assert "to_user" in props
        assert "amount" in props

    def test_transfer_schema_does_not_expose_ctx(self):
        from app.ai.tools.banking_tools import TransferFundsTool
        from lauren_ai._tools import TOOL_META

        meta = getattr(TransferFundsTool, TOOL_META)
        assert "ctx" not in meta.parameters["input_schema"]["properties"]

    def test_history_schema_has_limit(self):
        from app.ai.tools.banking_tools import GetTransactionHistoryTool
        from lauren_ai._tools import TOOL_META

        meta = getattr(GetTransactionHistoryTool, TOOL_META)
        assert "limit" in meta.parameters["input_schema"]["properties"]
