"""Unit tests for BankingCRMAgent and BankingTransferAgent metadata and configuration."""

from __future__ import annotations

import pytest

from app.ai.crm_agent import BankingCRMAgent
from app.ai.transfer_agent import BankingTransferAgent
from lauren_ai import USE_GUARDRAILS_META


class TestBankingCRMAgent:
    def test_has_agent_meta(self):
        assert hasattr(BankingCRMAgent, "__lauren_ai_agent__")

    def test_agent_meta_has_system_prompt(self):
        meta = getattr(BankingCRMAgent, "__lauren_ai_agent__")
        assert meta.system

    def test_agent_meta_has_max_turns(self):
        meta = getattr(BankingCRMAgent, "__lauren_ai_agent__")
        assert meta.config.max_turns is not None

    def test_system_prompt_mentions_securebank(self):
        meta = getattr(BankingCRMAgent, "__lauren_ai_agent__")
        assert "SecureBank" in meta.system or "bank" in meta.system.lower()

    def test_has_use_tools_meta(self):
        assert hasattr(BankingCRMAgent, "__lauren_ai_use_tools__") or hasattr(
            BankingCRMAgent, "__lauren_ai_agent__"
        )


class TestBankingTransferAgent:
    def test_has_agent_meta(self):
        assert hasattr(BankingTransferAgent, "__lauren_ai_agent__")

    def test_agent_meta_has_model(self):
        meta = getattr(BankingTransferAgent, "__lauren_ai_agent__")
        assert hasattr(meta, "model")

    def test_agent_meta_has_system_prompt(self):
        meta = getattr(BankingTransferAgent, "__lauren_ai_agent__")
        assert meta.config.system_prompt

    def test_system_prompt_mentions_transfer(self):
        meta = getattr(BankingTransferAgent, "__lauren_ai_agent__")
        assert "transfer" in meta.system.lower() or "bank" in meta.system.lower()


class TestBankingToolMetas:
    def test_get_balance_tool_has_meta(self):
        from app.ai.banking_tools import GetBalanceTool
        from lauren_ai._tools import TOOL_META
        assert hasattr(GetBalanceTool, TOOL_META)

    def test_transfer_funds_tool_has_meta(self):
        from app.ai.banking_tools import TransferFundsTool
        from lauren_ai._tools import TOOL_META
        assert hasattr(TransferFundsTool, TOOL_META)

    def test_get_history_tool_has_meta(self):
        from app.ai.banking_tools import GetTransactionHistoryTool
        from lauren_ai._tools import TOOL_META
        assert hasattr(GetTransactionHistoryTool, TOOL_META)

    def test_get_balance_schema_has_user_id(self):
        from app.ai.banking_tools import GetBalanceTool
        from lauren_ai._tools import TOOL_META
        meta = getattr(GetBalanceTool, TOOL_META)
        assert "user_id" in meta.parameters["input_schema"]["properties"]

    def test_transfer_schema_has_to_user_and_amount(self):
        from app.ai.banking_tools import TransferFundsTool
        from lauren_ai._tools import TOOL_META
        meta = getattr(TransferFundsTool, TOOL_META)
        props = meta.parameters["input_schema"]["properties"]
        assert "to_user" in props
        assert "amount" in props

    def test_transfer_schema_does_not_expose_ctx(self):
        from app.ai.banking_tools import TransferFundsTool
        from lauren_ai._tools import TOOL_META
        meta = getattr(TransferFundsTool, TOOL_META)
        assert "ctx" not in meta.parameters["input_schema"]["properties"]

    def test_history_schema_has_limit(self):
        from app.ai.banking_tools import GetTransactionHistoryTool
        from lauren_ai._tools import TOOL_META
        meta = getattr(GetTransactionHistoryTool, TOOL_META)
        assert "limit" in meta.parameters["input_schema"]["properties"]
